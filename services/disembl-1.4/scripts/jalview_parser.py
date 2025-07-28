import argparse
import enum
import re
import sys
from collections import namedtuple, OrderedDict


class GraphType(enum.Enum):
    BAR_GRAPH = 'BAR_GRAPH'
    LINE_GRAPH = 'LINE_GRAPH'
    NO_GRAPH = 'NO_GRAPH'


Graph = namedtuple('graph', 'type, label, description, values')
Graphline = namedtuple('graphline', 'value, label, colour')
Feature = namedtuple('feature', 'description, name, index, start, end, feature_type, score')


def run(args):
    result = read_file(open(args.input))
    if args.annot:
        with open(args.annot, 'w') as fp:
            print_annotations_file(result, fp)
    if args.feat:
        with open(args.feat, 'w') as fp:
            print_features_file(result, fp)


def read_file(file):
    result = OrderedDict()
    annots = None
    line = file.readline()
    while line:
        if line == '\n':
            line = file.readline()
            continue
        seq = re.match(r'^>\s?(.*\S)\s*$', line).group(1)
        coils = rem465 = hotloops = ()
        while True:
            line = file.readline()
            match = re.match(r'^# (COILS|REM465|HOTLOOPS)\s*((?:\d+-\d+(?:, )?)*)', line)
            if match is None: break
            ranges = [tuple(r.split('-')) for r in match.group(2).split(', ')] if match.group(2) else []
            if match.group(1) == 'COILS': coils = ranges
            elif match.group(1) == 'REM465': rem465 = ranges
            elif match.group(1) == 'HOTLOOPS': hotloops = ranges
        assert line == '# RESIDUE\tCOILS\tREM465\tHOTLOOPS\n'
        line = file.readline()
        annots = []
        while line:
            if not re.match(r'^[A-Za-z\-](?:\t\d+\.\d+){3}$', line): break
            residue, v_coil, v_rem465, v_hotloop = line.split()
            annots.append(v_rem465)
            line = file.readline()
        result[seq] = (coils, rem465, hotloops, annots)
    return result


def print_annotations_file(data, file=None):
    file = file or sys.stdout
    file.write('JALVIEW_ANNOTATION\n\n')
    for seq, (coils, rem465, hotloops, annots) in data.items():
        file.write('SEQUENCE_REF\t{}\n'.format(seq))
        graph = Graph(
            type=GraphType.LINE_GRAPH,
            label="DisemblWS (REM465)",
            description="<html>Protein Disorder with DisemblWS - raw scores<br/>"
                                    "Above 0.1204 indicates disorder</html>",
            values=annots
        )
        graphline = Graphline(
            value='0.1204', label='Above 0.1204 indicates disorder', colour='ff0000'
        )
        print_annotation_row(graph, graphline, '2385b0', file=file)
        file.write("\n")


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


def print_features_file(data, file=None):
    file = file or sys.stdout
    file.write(
        'HOTLOOPS\t511e29\n'
        'REM465\t1e5146\n'
        'COILS\tcfdb48\n\n'
        'STARTGROUP\tDisemblWS\n'
    )
    for seq, (coils, rem465, hotloops, annots) in data.items():
        groups = [coils, rem465, hotloops]
        descs = ["Random coil", "Missing density", "Flexible loops"]
        types = ["COILS", "REM465", "HOTLOOPS"]
        for group, desc, ft_type in zip(groups, descs, types):
            for region in group:
                feature = Feature(
                    description=desc,
                    name=seq,
                    index='-1',
                    start=region[0],
                    end=region[1],
                    feature_type=ft_type,
                    score=None
                )
                print_feature_row(feature, file=file)
        file.write('\n')
    file.write('ENDGROUP\tDisemblWS\n')


def print_feature_row(feature, file=None):
    def is_not_none(val): return val is not None
    print(str.join('\t', map(str, filter(is_not_none, feature))), file=file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--annot', '-a')
    parser.add_argument('--feat', '-f')
    args = parser.parse_args()
    run(args)
