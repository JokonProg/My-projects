import json

percentage = 0.8
enter = '\n'


def parse_file() -> list:
    file = open('select.csv', mode='r')
    lines = json.loads(file.read())
    file.close()
    return lines


def split_headers(input_lines: list) -> list:
    result = []
    for headers in input_lines:
        result.append(headers.split(','))
    return result


def count_headers(input_headers: list) -> dict:
    result = {}
    for headers in input_headers:
        for header in headers.split(','):
            if result.get(header, None):
                result[header] = result[header] + 1
            else:
                result[header] = 1
    return result


def count_percentage(headers_counted_input: dict, input_lines: list) -> dict:
    result = {}
    for header in headers_counted_input:
        result[header] = (headers_counted_input[header]/len(input_lines))
    return result


def prepare_headers_ciphers(input_lines: list, headers_percentage: dict, percentage: float) -> set:
    result = set()
    for headers in input_lines:
        headers_cipher = []
        for header in headers.split(','):
            if headers_percentage[header] > percentage:
                headers_cipher.append(header)
        result.add(str.join(',', headers_cipher))
    return result


def get_headers_ciphers(input_headers: str, headers_percentage: dict, percentage: float) -> str:
    result = []
    for header in input_headers.split(','):
        if headers_percentage[header] > percentage:
            result.append(header)
    return ','.join(result)


if __name__ == '__main__':
    lines = parse_file()
    splitted_headers = split_headers(lines)
    headers_counted = count_headers(lines)
    headers_percentage = count_percentage(headers_counted, lines)
    headers_ciphers = prepare_headers_ciphers(lines, headers_percentage, percentage)
    final_result = set()
    for cipher in headers_ciphers:
        intermediate_result = []
        for headers in lines:
            if cipher == get_headers_ciphers(headers, headers_percentage, percentage):
                intermediate_result.append(headers)
        intermediate_result.sort()
        if len(intermediate_result) <= 2:
            second_headers_ciphers = cipher
            final_result.add(cipher)
            print(f'For {cipher}:\n{enter.join(intermediate_result)}\nGot:\n{second_headers_ciphers}\n\n\n')
        elif len(intermediate_result) == 3:
            second_lines = intermediate_result
            second_splitted_headers = split_headers(second_lines)
            second_headers_counted = count_headers(second_lines)
            second_headers_percentage = count_percentage(second_headers_counted, second_lines)
            second_headers_ciphers = prepare_headers_ciphers(second_lines, second_headers_percentage, 0.3)
            [final_result.add(header) for header in second_headers_ciphers]
            print(f'For {cipher}:\n{enter.join(intermediate_result)}\nGot:\n{enter.join(second_headers_ciphers)}\n\n\n')
        elif len(intermediate_result) > 3:
            second_lines = intermediate_result
            second_splitted_headers = split_headers(second_lines)
            second_headers_counted = count_headers(second_lines)
            second_headers_percentage = count_percentage(second_headers_counted, second_lines)
            second_headers_ciphers = prepare_headers_ciphers(second_lines, second_headers_percentage, 0.5)
            [final_result.add(header) for header in second_headers_ciphers]
            print(f'For {cipher}:\n{enter.join(intermediate_result)}\nGot:\n{enter.join(second_headers_ciphers)}\n\n\n')
        line = "\n".join(second_headers_ciphers)
    print('Intermediate result:\n', str.join('\n', headers_ciphers), '\n\n\n')
    print('Final result:')
    final_result = list(final_result)
    final_result.sort()
    print('\n'.join(final_result))

    exit(0)
