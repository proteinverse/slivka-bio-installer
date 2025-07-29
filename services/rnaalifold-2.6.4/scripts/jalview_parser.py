import argparse
import enum
import re
import sys
from collections import defaultdict, namedtuple
from operator import itemgetter


class GraphType(enum.Enum):
    BAR_GRAPH = 'BAR_GRAPH'
    LINE_GRAPH = 'LINE_GRAPH'
    NO_GRAPH = 'NO_GRAPH'


Graph = namedtuple('graph', 'type, label, description, values')
Graphline = namedtuple('graphline', 'value, label, colour')


float_pat = r'[+-]?(?:[0-9]*\.)?[0-9]+'
seq_pat = r'[_\-a-zA-Z]+'
structure_pat = r'[\.(){}\[\],]+'


def run(args):
    data = read_structures(open(args.input))
    if args.alifold:
        data['contacts'] = read_alifold(open(args.alifold))
    if args.annot:
        with open(args.annot, 'w') as fp:
            print_annotations(data, fp)


def read_structures(file):
    result = {}
    # first line is always an alignment
    alignment = file.readline().strip()
    assert re.match(rf'{seq_pat}$', alignment), "Alignment expected."
    result['alignment'] = alignment
    # second line is always a mfe
    structure, mfe_energy = file.readline().split(None, 1)
    assert re.match(rf'{structure_pat}$', structure), "MFE structure expected"
    match = re.match(rf'\(({float_pat}) *= *({float_pat}) *\+ *({float_pat})\)$', mfe_energy)
    assert match, "Energies expected after mfe structure"
    result['mfe'] = structure, match.group(1, 2, 3)
    # rest of the file depends on the parameters
    for line in file:
        if line == '\n':
            continue
        match = re.match(structure_pat, line)
        if match:
            structure = match.group(0)
            energy = line[match.end() + 1:]
            match = re.match(rf'\[({float_pat})\]$', energy)
            if match:
                result['partition'] = structure, (match.group(1),)
                continue
            match = re.match(rf'{{({float_pat}) *= *({float_pat}) *\+ *({float_pat}) *(d={float_pat})}}', energy)
            if match:
                result['centroid'] = structure, match.group(1, 2, 3, 4)
                continue
            match = re.match(rf'{{({float_pat}) *= *({float_pat}) *\+ *({float_pat}) *(MEA={float_pat})}}', energy)
            if match:
                result['mea'] = structure, match.group(1, 2, 3, 4)
                continue
            raise ValueError(f"Unrecognised line \"{line}\"")
        pattern = (rf'\s*frequency of mfe structure in ensemble ({float_pat}); '
                                rf'ensemble diversity ({float_pat})\s*')
        match = re.match(pattern, line)
        if match:
            structure, scores = result['partition']
            result['partition'] = structure, scores + match.group(1, 2)
    return result


def read_alifold(file):
    # skip header
    file.readline()
    file.readline()
    contacts = defaultdict(list)
    for line in file:
        cols = line.split()
        assert len(cols) >= 6 or re.match(structure_pat, line), \
            "Contact probabilities expected"
        if len(cols) < 6:
            break
        probability = float(cols[3][:-1])
        item = int(cols[0]), int(cols[1]), probability
        if probability > 0:
            contacts[item[0]].append(item)
            contacts[item[1]].append(item)
    for items in contacts.values():
        items.sort(key=itemgetter(2), reverse=True)
    return contacts


def print_annotations(data, file=sys.stdout):
    file.write("JALVIEW_ANNOTATION\n\n")
    print(
        'NO_GRAPH', 'RNAalifold Consensus',
        'Consensus alignment produced by RNAalifold',
        '|'.join(data['alignment']), sep='\t', file=file
    )
    structure, scores = data['mfe']
    print(
        'NO_GRAPH', 'MFE structure', 
        'Minimum free energy structure. Energy: %s = %s + %s' % scores,
        structure_to_annotations(structure), sep='\t', file=file
    )
    if 'partition' in data and 'contacts' in data:
        structure, scores = data['partition']
        contacts = data['contacts']
        graph = []
        for i, char in enumerate(structure):
            i = i + 1
            if i in contacts:
                # second value (probability) of zeroth item (highest) of i-th column
                value = contacts[i][0][2] 
                tooltip = ('%i->%i: %.1f%%' % it for it in contacts[i])
                tooltip = str.join('; ', tooltip)
            else:
                value = 0.0
                tooltip = 'No data'
            graph.append(f'{value:.1f},{char},{tooltip}')
        print(
            'BAR_GRAPH', 'Contact Probabilities',
            "Base Pair Contact Probabilities. " +
            "Energy of Ensemble: %s, frequency: %s, diversity: %s." % scores,
            "|".join(graph), sep='\t', file=file
        )
    if 'centroid' in data:
        structure, scores = data['centroid']
        print(
            'NO_GRAPH', 'Centroid Structure',
            'Centroid Structure. Energy: %s = %s + %s, %s' % scores,
            structure_to_annotations(structure), sep='\t', file=file
        )
    if 'mea' in data:
        structure, scores = data['mea']
        print(
            "NO_GRAPH", "MEA Structure",
            "Maximum Expected Accuracy Values. %s = %s + %s, %s" % scores,
            structure_to_annotations(structure), sep='\t', file=file
        )
    file.write('\n')
    props = "scaletofit=true\tshowalllabs=true\tcentrelabs=false"
    if 'mfe' in data:
        print(f"ROWPROPERTIES\tMFE Structure\t{props}", file=file)
    if 'centroid' in data:
        print(f"ROWPROPERTIES\tCentroid Structure\t{props}", file=file)
    if 'mea' in data:
        print(f"ROWPROPERTIES\tMEA Structure\t{props}", file=file)


def structure_to_annotations(structure):
    tokens = [
        f'S,{it}' if it != '.' else f',{it}' for it in structure
    ]
    return '|'.join(tokens)


def print_annotation_row(graph, graphline=None, colour=None, file=None):
    row = "{type}\t{label}\t{description}\t{values}".format(
        type=graph.type.name,
        label=graph.label,
        description=graph.description,
        values=str.join('|', map('{0},{0}'.format, graph.values))
    )
    print(row, file=file)
    if graph.type == GraphType.LINE_GRAPH:
        if graphline is not None:
            print('GRAPHLINE\t{name}\t{value}\t{label}\t{colour}'.format(
                name=graph.label, value=graphline.value, label=graphline.label,
                colour=graphline.colour
            ), file=file)
        if colour is not None:
            print('COLOUR\t{name}\t{colour}'.format(name=graph.label, colour=colour), file=file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--alifold')
    parser.add_argument('input')
    parser.add_argument('annot')
    args = parser.parse_args()
    run(args)
