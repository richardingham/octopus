# Twisted Imports
from twisted.internet import defer
from twisted.python import log

def makeFinder (cls, table, _column_spec):
    _column_names = _column_spec.keys()
    _column_sql = {n: (c['sql'] if 'sql' in c else n) for n, c in _column_spec.items()}
    _column_valfn = {n: (c['modifier'] if 'modifier' in c else None) for n, c in _column_spec.items()}

    _operators = {
        'eq': '=',
        'lt': '<',
        'lte': '<=',
        'gt': '>',
        'gte': '>=',
        'like': 'LIKE'
    }

    def _result (column, name):
        return (name, _column_spec[name]['type'](column))

    def find (filters = None, order = None, start = 0, limit = None, default_search = None, fetch_columns = None, return_counts = True):
        search_columns = []
        search_clause = []
        search_parameters = []
        default_search_clause = []
        default_search_parameters = []
        sort_clause = []
        fetch_columns = fetch_columns or _column_names
        extra_filter_columns = set()

        for filter in (filters or []):
            try:
                column_name = filter['column']
                if column_name not in _column_names:
                    continue

                if 'operator' in _column_spec[column_name]:
                    operator = _column_spec[column_name]['operator']
                elif 'operator' in filter and filter['operator'] in _operators:
                    operator = ' ' + _operators[filter['operator']] + ' ?'
                else:
                    operator = ' = ?'

                if _column_valfn[column_name] is not None:
                    filter['value'] = _column_valfn[column_name](filter['value'])

                search_parameters.append(filter['value'])
                search_clause.append(column_name + operator)

                if 'sql' in _column_spec[column_name]:
                    extra_filter_columns.add(column_name)

            except KeyError:
                log.err()
                pass

        for column, value in (default_search or {}).items():
            try:
                if 'operator' in value:
                    operator = ' ' + _operators[value['operator']] + ' ?'
                else:
                    operator = ' = ?'

                default_search_parameters.append(value['value'])
                default_search_clause.append(column + operator)
            except KeyError:
                continue

        for sort in (order or []):
            try:
                if sort['dir'] == 'desc':
                    direction = ' DESC'
                else:
                    direction = ' ASC'

                if sort['column'] in _column_names:
                    sort_clause.append(sort['column'] + direction)

                if 'sql' in _column_spec[sort['column']]:
                    extra_filter_columns.add(sort['column'])

            except KeyError:
                pass

        search_clause.extend(default_search_clause)
        search_parameters.extend(default_search_parameters)

        query = ['SELECT', ', '.join([_column_sql[name] for name in fetch_columns]), 'FROM', table]

        if len(search_clause):
            query.extend(('WHERE', ' AND '.join(search_clause)))

        if len(sort_clause):
            query.extend(('ORDER BY', ', '.join(sort_clause)))

        limit_parameters = []
        if limit is not None:
            query.append('LIMIT ?')
            limit_parameters.append(limit)
        if start > 0:
            query.append('OFFSET ?')
            limit_parameters.append(start)

        if return_counts:
            def _done (results):
                rows, count, count_all = results
                return {
                    'recordsTotal': count_all[0][0],
                    'recordsFiltered': count[0][0],
                    'data': [
                        dict(map(_result, row, fetch_columns))
                        for row in rows
                    ]
                }

            def _error (failure):
                log.err(failure)
                return {
                    'error': str(failure)
                }

            count_columns = ['COUNT(*)'] + [_column_sql[name] for name in extra_filter_columns]
            count_query = ['SELECT', ', '.join(count_columns), 'FROM', table]
            count_all_query = ['SELECT', ', '.join(count_columns), 'FROM', table]

            if len(search_clause):
                count_query.extend(('WHERE', ' AND '.join(search_clause)))
                count_all_query.extend(('WHERE', ' AND '.join(default_search_clause)))

            return defer.gatherResults([
                cls.db.runQuery(' '.join(query), search_parameters + limit_parameters),
                cls.db.runQuery(' '.join(count_query), search_parameters),
                cls.db.runQuery(' '.join(count_all_query), default_search_parameters),
            ]).addCallback(_done).addErrback(_error)
        else:
            def _done (rows):
                return [
                    dict(map(_result, row, fetch_columns))
                    for row in rows
                ]

            return cls.db.runQuery(' '.join(query), search_parameters + limit_parameters).addCallback(_done)
    return find
