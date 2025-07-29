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


def run(args):
    annotations = read_annotations(open(args.input))
    if args.annot:
        with open(args.annot, 'w') as fp:
            print_annotations_file(annotations, fp)


def read_annotations(file):
    annotations = OrderedDict()
    for line in file:
        if line == '\n': continue
        m = re.match(r'^#(\w+) ((?:-?\d+\.\d+ ?)+)$', line)
        annotations[m.group(1)] = m.group(2).split()
    return annotations


def print_annotations_file(annotations, file=None):
    file = file or sys.stdout
    file.write('JALVIEW_ANNOTATION\n\n')
    for method, values in annotations.items():
        graph = Graph(GraphType.BAR_GRAPH, method, method, values)
        print_annotation_row(graph, file=file)


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
    parser.add_argument('--annot', '-a')
    parser.add_argument('input')

    args = parser.parse_args()
    run(args)
