import datetime
import dateutil.parser


def equal_dicts(d1, d2, compare_by_keys):
    if not d1 or not d2:
        return d1 == d2
    return filtered_dict(d1, compare_by_keys) == \
           filtered_dict(d2, compare_by_keys)


def filtered_dict(d, filter_keys):
    if not d:
        return d
    return {k: v for k, v in d.items() if k in filter_keys}


def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value


def parse_timestamp_string(ts_string):
    # return datetime.datetime.strptime(ts_string, '%Y-%m-%dT%H:%M:%SZ')
    return dateutil.parser.isoparse(ts_string)


def local_now():
    LOCAL_TIMEZONE = datetime.datetime.now().astimezone().tzinfo
    return datetime.datetime.now(LOCAL_TIMEZONE)
