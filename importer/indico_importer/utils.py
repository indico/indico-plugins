def parse_datetime(string):
        split_datetime = string[0].split('T')
        if len(split_datetime) > 1:
            return {'date': string[0].split('T')[0],
                    'time': string[0].split('T')[1]}
        else:
            return {'date': string[0].split('T')[0],
                    'time': '00:00'}
