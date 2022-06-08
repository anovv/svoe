import json


def save_stats(stats):
    # TODO
    # path = f'resources-estimation-{datetime.datetime.now().strftime("%d-%m-%Y-%H:%M:%S")}.json'
    path = 'resources-estimation.json'
    with open(path, 'w+') as outfile:
        json.dump(stats, outfile, indent=4, sort_keys=True)
    print(f'Saved stats to {path}')


def equal_dicts(d1, d2, compare_by_keys):
    if not d1 or not d2:
        return d1 == d2
    return filtered_dict(d1, compare_by_keys) == \
           filtered_dict(d2, compare_by_keys)


def filtered_dict(d, filter_keys):
    if not d:
        return d
    return {k: v for k, v in d.items() if k in filter_keys}
