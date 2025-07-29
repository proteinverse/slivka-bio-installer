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
    if args.feat:
        with open(args.feat, 'w') as fp:
            print_features_file(result, fp)
    if args.annot:
        with open(args.annot, 'w') as fp:
            print_annotations_file(result, fp)


def read_file(file):
    result = OrderedDict()
    for line in file:
        if line == '\n':
            continue
        seq = re.match(r'^>\s?(.*\S)\s*$', line).group(1)
        doms = re.match(r'^# GlobDoms\s*((?:\d+-\d+(?:, )?)*)', next(file)).group(1)
        doms = [tuple(r.split('-')) for r in doms.split(', ')] if doms else []
        dis = re.match(r'^# Disorder\s*((?:\d+-\d+(?:, )?)*)', next(file)).group(1)
        dis = [tuple(r.split('-')) for r in dis.split(', ')] if dis else []
        next(file)
        annots = []
        for line in file:
            if line == '\n': break
            residue, dydx, raw, smoothed = line.split()
            annots.append(dydx)
        result[seq] = (doms, dis, annots)
    return result


def print_annotations_file(data, file=None):
    file = file or sys.stdout
    file.write('JALVIEW_ANNOTATION\n\n')
    for seq, (doms, dis, annots) in data.items():
        file.write('SEQUENCE_REF\t{}\n'.format(seq))
        graph = Graph(
            type=GraphType.LINE_GRAPH,
            label="GlobPlotWS (Dydx)",
            description="<html>Protein Disorder with GlobPlotWS - raw scores<br/>"
                                    "Above 0.0 indicates disorder</html>",
            values=annots
        )
        graphline = Graphline(
            value='0.0', label='Above 0.0 indicates disorder', colour='ff0000'
        )
        print_annotation_row(graph, graphline, '8123cc', file=file)
        file.write('\n')


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
        'Protein Disorder\tc5b938\n'
        'Globular Domain\t876d2a\n\n'
        'STARTGROUP\tGlobPlotWS\n'
    )
    for seq, (doms, dis, annots) in data.items():
        for domain in doms:
            feature = Feature(
                description="Predicted globular domain",
                name=seq,
                index='-1',
                start=domain[0],
                end=domain[1],
                feature_type="Globular Domain",
                score=None
            )
            print_feature_row(feature, file)
        for region in dis:
            feature = Feature(
                description="Probable unstructured peptide region",
                name=seq,
                index='-1',
                start=region[0],
                end=region[1],
                feature_type="Protein Disorder",
                score=None
            )
            print_feature_row(feature, file=file)
    file.write('ENDGROUP\tGlobPlotWS\n')


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
