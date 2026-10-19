#!/usr/bin/env python

import argparse

from gwas_sumstats_tools.interfaces.metadata import MetadataClient


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-i', help='Input metadata yaml file')
    argparser.add_argument('-o', help='output metadata yaml file')
    argparser.add_argument('-e', help='Edit mode, provide params to edit e.g. `-GWASID GCST123456` to edit/add that value', action='store_true')
    _, unknown = argparser.parse_known_args()
    for arg in unknown:
        if arg.startswith(("-", "--")):
            arg_pair = arg.split('=')
            argparser.add_argument(arg_pair[0])
    args = argparser.parse_args()
    known_args = {'i', 'o', 'e'}
    in_file = args.i
    out_file = args.o
    edit_mode = args.e
    m = MetadataClient(in_file=in_file, out_file=out_file)
    if in_file:
        m.from_file()
        print(f"===========\nMetadata in\n===========\n{m}")
    if edit_mode:
        data_dict = {k: v for k, v in vars(args).items() if k not in known_args}
        m.update_metadata(data_dict)
    if out_file:
        print(f"============\nMetadata out\n============\n{m}")
        m.to_file()


if __name__ == "__main__":
    main()
