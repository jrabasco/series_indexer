#!/usr/bin/python3

import sys, os
import re
import argparse
import ast
import subprocess

def parse_args(argv):
    parser = argparse.ArgumentParser(description='Index series folder')
    parser.add_argument('-i', '--index', dest='do_index', action='store_true', help='Create index')
    parser.add_argument('-p', '--pattern', nargs='?', help='Pattern for season/episode extraction')
    parser.add_argument('-d', '--directory', help='Directory')
    parser.add_argument('-n', '--next', dest='next', default='0', type=int, help='Move cursor to next episode (APPLIED BEFORE WATCH)')
    parser.add_argument('-b', '--back', dest='back', default='0', type=int, help='Move cursor to previous episode (APPLIED BEFORE WATCH)')
    parser.add_argument('-w', '--watch', dest='do_watch', action='store_true', help='Watch episode then move cursor to next episode')
    parser.add_argument('-s', '--show', dest='do_show', action='store_true', help='Show current episode number')
    parser.add_argument('-e', '--executable', default='mpv', help='Executable to watch')

    args = parser.parse_args(argv[1:])

    if args.do_index and args.pattern is None:
        parser.error("Pattern must be defined in order to index.")

    return args

def main(argv):
    args = parse_args(argv)
    if args.do_index:
        print("Indexing...")
        index(args.directory, args.pattern.upper())

    if args.next > 0:
        for i in range(args.next):
            apply_next(args.directory)

    if args.back > 0:
        for i in range(args.back):
            apply_back(args.directory)

    if args.do_watch:
        watch(args.directory, args.executable)

    if args.do_show:
        show_cursor(args.directory)

def index(directory, pattern):
    permitted_files = [".avi", ".mp4", ".mkv"]
    ep_pos = pattern.find("E")
    s_pos = pattern.find("S")

    if ep_pos == -1 or s_pos == -1:
        print("No S or E.", file=sys.stderr)
        sys.exit(1)

    pattern = generate_regexp(pattern)
    ep_pos = 1 if ep_pos > s_pos else 0
    s_pos = 1 - ep_pos

    index = {}
    index_path = os.path.join(directory, ".index")

    if os.path.isfile(index_path):
        print("Found index!")
        with open(index_path, "r") as f:
            index = ast.literal_eval(f.read())

    print(pattern)

    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if not any([filename.endswith(term) for term in permitted_files]):
                continue

            print(filename)
            groups = re.match(pattern, filename).groups()
            print(groups)
            season = int(groups[s_pos])
            episode = int(groups[ep_pos])

            if season not in index:
                index[season] = {}

            index[season][episode] = os.path.join(dirpath, filename)

    if "cursor" not in index:
        first_season = min(index.keys())
        first_episode = min(index[first_season].keys())
        index["cursor"] = (first_season, first_episode)

    with open(index_path, "w+") as f:
        f.write(repr(index))

def apply_back(directory):
    index_path = os.path.join(directory, ".index")
    with open(index_path, "r") as f:
        index = ast.literal_eval(f.read())

    cur_s, cur_ep = index["cursor"]
    poss_ep = [i for i in index[cur_s].keys() if i < cur_ep]

    if len(poss_ep) == 0:
        if (cur_s - 1) in index:
            prev_s = cur_s - 1
            prev_ep = max(index[prev_s].keys())
        else:
            prev_s = cur_s
            prev_ep = cur_ep
    else:
        prev_s = cur_s
        prev_ep = max(poss_ep)

    cursor = (prev_s, prev_ep)
    print("New cursor is", cursor)
    index["cursor"] = cursor
    with open(index_path, "w+") as f:
        f.write(repr(index))


def apply_next(directory):
    index_path = os.path.join(directory, ".index")
    with open(index_path, "r") as f:
        index = ast.literal_eval(f.read())

    cur_s, cur_ep = index["cursor"]
    poss_ep = [i for i in index[cur_s].keys() if i > cur_ep]

    if len(poss_ep) == 0:
        if (cur_s + 1) in index:
            next_s = cur_s + 1
            next_ep = min(index[next_s].keys())
        else:
            next_s = cur_s
            next_ep = cur_ep
    else:
        next_s = cur_s
        next_ep = min(poss_ep)

    cursor = (next_s, next_ep)
    print("New cursor is", cursor)
    index["cursor"] = cursor
    with open(index_path, "w+") as f:
        f.write(repr(index))

def show_cursor(directory):
    index_path = os.path.join(directory, ".index")
    with open(index_path, "r") as f:
        index = ast.literal_eval(f.read())

    print("Cursor is", index["cursor"])

def watch(directory, executable):
    index_path = os.path.join(directory, ".index")
    with open(index_path, "r") as f:
        index = ast.literal_eval(f.read())
    cursor = index["cursor"]
    print("Watching", cursor)
    season, episode = cursor
    subprocess.run([executable, index[season][episode]])
    apply_next(directory)

def generate_regexp(pattern):
    add_paren = re.compile("(E+|S+)")
    with_paren = add_paren.sub(r"(\1)", pattern)

    replace_digit = re.compile("(E|S)")
    return ".*" + replace_digit.sub(r"\d", with_paren) + ".*"

if __name__ == "__main__":
    main(sys.argv)