#!/usr/bin/env python3

import sqlite3
import plotly.graph_objects as go

DBNAME = 'scp.db'

def parse_command(tokens):
    tokens = tokens[:]
    if len(tokens) == 0:
        return ""
    cmd = tokens[0]
    tokens = tokens[1:]
    core_inner_query = 'SELECT `Index`, Title, URL, ObjectClass, Comments, Rating, TagName FROM items INNER JOIN itemtags ON items.Id = itemtags.ItemId'
    if cmd == "items":
        inner_query = 'SELECT `Index`, Title, URL, ObjectClass, Comments, Rating, GROUP_CONCAT(TagName) as Tags FROM (%s) GROUP BY `Index`' % (core_inner_query, )
        sql = "SELECT `Index`, Title, ObjectClass, Comments, Rating, Tags, URL FROM (%s) WHERE %s ORDER BY %s %s limit %d"
        order_column = "Rating"
        order_scheme = "DESC"
        top_n = 10
        where_clause = "1=1"
        while len(tokens) > 0:
            token = tokens[0]
            tokens = tokens[1:]
            if token == "rating":
                # `rating` is the default option
                continue
            elif token == "comments":
                order_column = "Comments"
                continue
            elif token == "top" or token == "bottom":
                if token == "bottom":
                    order_scheme = "ASC"
                continue
                if len(tokens) == 0:
                    return ""
                token = tokens[0]
                tokens = tokens[1:]
                if not token.isdigit():
                    return ""
                top_n = int(token)
                continue
            elif token == "none":
                continue
            elif token.startswith("tag="):
                where_clause = "Tags LIKE '%" + token[4:].lower() + "%'"
                continue
            elif token.startswith("class="):
                where_clause = "ObjectClass = '" + token[6:] + "'"
                continue
            elif token.startswith("index="):
                where_clause = "`Index` = '" + token[6:].upper() + "'"
                continue
            elif token == 'barplot':
                continue
            else:
                if token.isdigit():
                    top_n = int(token)
                else:
                    # unexpected token
                    return ""
        sql = sql % (inner_query, where_clause, order_column, order_scheme, top_n)
        return sql
    elif cmd == "tags":
        sql = "SELECT * FROM (%s) WHERE %s ORDER BY %s %s limit %d"
        order_column = "AvgRating"
        order_scheme = "DESC"
        top_n = 10
        where_clause = "1=1"
        while len(tokens) > 0:
            token = tokens[0]
            tokens = tokens[1:]
            if token == "rating":
                # `rating` is the default option
                continue
            elif token == "comments":
                order_column = "AvgComments"
                continue
            elif token == "top" or token == "bottom":
                if token == "bottom":
                    order_scheme = "ASC"
                continue
                if len(tokens) == 0:
                    return ""
                token = tokens[0]
                tokens = tokens[1:]
                if not token.isdigit():
                    return ""
                top_n = int(token)
                continue
            elif token == "none":
                continue
            elif token.startswith("class="):
                where_clause = "ObjectClass = '" + token[6:] + "'"
                continue
            elif token == 'barplot':
                continue
            else:
                if token.isdigit():
                    top_n = int(token)
                else:
                    # unexpected token
                    return ""
        inner_query = core_inner_query + ' WHERE ' + where_clause
        sql = 'SELECT TagName, AVG(Comments) AS AvgComments, AVG(Rating) AS AvgRating FROM (%s) GROUP BY TagName ORDER BY %s %s LIMIT %d' % (inner_query, order_column, order_scheme, top_n)
        return sql
    else:
        return ""


def process_command(command):
    sql = parse_command(command.split(' '))
    if sql == "":
        return []
    # print(sql)
    connection = sqlite3.connect(DBNAME)
    cursor = connection.cursor()
    result = cursor.execute(sql).fetchall()
    connection.close()
    return result



def load_help_text():
    with open('help.txt') as f:
        return f.read()

DEFAULT_COLUMN_WIDTH = 20

def array_output(arr, widths=None):
    if len(arr) == 0:
        return
    num_col = len(arr[0])
    if widths is None:
        widths = [DEFAULT_COLUMN_WIDTH for i in range(num_col)]
    fmt = ''
    for i in range(num_col - 1):
        fmt += '{%d:<%d}' % (i, widths[i])
    fmt += '{%d}' % (num_col - 1,)
    def str_trunc(x, w):
        if isinstance(x, float):
            if x < 1:
                y = "%.2d" % (100*x,) + '%'
            else:
                y = "%.1f" % (x,)
        else:
            y = str(x)
        if len(y) >= w - 1:
            y = y[:w - 4] + '...'
        return y
    for row in arr:
        new_row = [str_trunc(row[i], widths[i]) for i in range(len(row))]
        print(fmt.format(*new_row))

def items_output(res):
    #`Index`, Title, ObjectClass, Comments, Rating, Tags, URL
    header = [["Index", "Title", "ObjectClass", "Comments", "Rating", "Tags", "URL"]]
    widths = [10, 25, 13, 11, 9, 80, 33]
    total_width = sum(widths)
    array_output(header, widths)
    lb = "=" * total_width
    print(lb)
    _res = res
    res = []
    for it in _res:
        res.append(list(it))
    new_res = []
    for it in res:
        if it[1].strip() == "":
            it[1] = "<none>"
        if it[2].strip() == "":
            it[2] = "<none>"
        tags = it[5].split(',')
        if len(tags) == 0:
            new_res.append(it)
            continue
        tags_line = tags[0]
        tags = tags[1:]
        while len(tags) > 0:
            while len(tags) > 0 and len(tags_line) + 1 + len(tags[0]) < widths[-2] - 1:
                tags_line += ',' + tags[0]
                tags = tags[1:]
            if len(tags) > 0:
                tags_line += ','
            it[5] = tags_line
            new_res.append(it)
            it = ["" for _ in range(len(widths))]
            tags_line = ""
            if len(tags) > 0:
                tags_line = tags[0]
                tags = tags[1:]
        if tags_line != "":
            it[5] = tags_line
            new_res.append(it)
    array_output(new_res, widths)

def tags_output(res):
    header = [["TagName", "AvgComments", "AvgRating"]]
    widths = [40, 15, 15]
    total_width = sum(widths)
    array_output(header, widths)
    lb = "=" * total_width
    print(lb)
    array_output(res, widths)

def barplot_output(resp, cmd_tokens):
    if 'tags' in cmd_tokens:
        x = [row[0] for row in resp]
        xaxes = 'TagName'
        if 'comments' in cmd_tokens:
            y = [row[1] for row in resp]
            yaxes = 'Average Number of Comments'
        else:
            y = [row[2] for row in resp]
            yaxes = 'Average Rating'
    elif 'items' in cmd_tokens:
        x = [row[0] for row in resp]
        xaxes = 'SCP Item Index'
        if 'comments' in cmd_tokens:
            y = [row[3] for row in resp]
            yaxes = 'Number of Comments'
        else:
            y = [row[4] for row in resp]
            yaxes = 'Rating'
    fig = go.Figure([go.Bar(x=x, y=y)])
    fig.update_xaxes(title_text=xaxes)
    fig.update_yaxes(title_text=yaxes)
    fig.show()


def interactive_prompt():
    help_text = load_help_text()
    response = ''
    while response != 'exit':
        response = input('Enter a command or "help" for help: ')

        if response == 'help':
            print(help_text)
            continue
        elif response == 'exit':
            continue
        else:
            response = response.strip()
            tokens = response.split(' ')
            if parse_command(tokens) == "":
                print("Invalid command! Please correct your input and try again.")
                continue
            resp = process_command(response)
            if 'barplot' in tokens:
                barplot_output(resp, tokens)
            else:
                if tokens[0] == "items":
                    items_output(resp)
                elif tokens[0] == "tags":
                    tags_output(resp)

if __name__=="__main__":
    interactive_prompt()
