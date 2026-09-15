import pathlib
p = pathlib.Path('scripts/benchmark_acceptance.py')
t = p.read_text()
old = "    parser.add_argument('--set', required=True, choices=['development', 'holdout', 'all'])"
assert t.count(old) == 1, t.count(old)
new = "    parser.add_argument('--set', required=True, help=\"a set name from the registry (development, holdout, fresh_holdout) or 'all'\")"
t = t.replace(old, new, 1)
old_main = """    document = json.loads(args.registry.read_text())
    if args.set == 'all':
        target = args.output
        for name in ('development', 'holdout'):
            run_set(name, _selected(document['sets'][name], args.case), target / name)
    else:
        run_set(args.set, _selected(document['sets'][args.set], args.case), args.output)"""
assert t.count(old_main) == 1, t.count(old_main)
new_main = """    document = json.loads(args.registry.read_text())
    if args.set == 'all':
        target = args.output
        for name in sorted(document['sets']):
            run_set(name, _selected(document['sets'][name], args.case), target / name)
    elif args.set not in document['sets']:
        raise SystemExit('No declared set named ' + args.set + '. The registry has: ' + ', '.join(sorted(document['sets'])))
    else:
        run_set(args.set, _selected(document['sets'][args.set], args.case), args.output)"""
t = t.replace(old_main, new_main, 1)
p.write_text(t)
print('patched')