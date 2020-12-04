#!/usr/bin/env python3

from fetch_utils import make_request_with_cache
import sqlite3
from bs4 import BeautifulSoup

def get_scp_item_url(idx):
    if idx <= 999:
        return 'http://www.scpwiki.com/scp-%03d' % (idx,)
    else:
        return 'http://www.scpwiki.com/scp-%04d' % (idx,)

def get_scp_item_serie_url(idx):
    serie_idx = idx // 1000
    if serie_idx == 0:
        return 'http://www.scpwiki.com/scp-series'
    else:
        return 'http://www.scpwiki.com/scp-series-' + str(serie_idx + 1)

DB_FILENAME = "scp.db"

def open_db():
    """ Open an existing sqlite3 database, or create a new one if there is no present. """
    try:
        conn = sqlite3.connect(DB_FILENAME)
        conn.execute("""
CREATE TABLE IF NOT EXISTS "items" (
  "Id" INTEGER NOT NULL,
  "Index" TEXT,
  "Title" TEXT,
  "URL" TEXT,
  "ObjectClass" text,
  "Comments" integer,
  "Rating" integer,
  PRIMARY KEY ("Id")
);
        """)
        conn.execute("""
CREATE TABLE IF NOT EXISTS "itemtags" (
  "Id" INTEGER NOT NULL,
  "ItemId" INTEGER,
  "TagName" TEXT,
  PRIMARY KEY ("Id")
);
        """)
        conn.commit()
    except sqlite3.Error as ex:
        print(ex)
        return None
    return conn

FETCH_RANGE = 2000

def fetch_item(idx):
    item_page_url = get_scp_item_url(idx)
    item_page_soup = BeautifulSoup(make_request_with_cache(item_page_url, {}), "lxml")
    item_serie_page_url = get_scp_item_serie_url(idx)
    item_serie_page_soup = BeautifulSoup(make_request_with_cache(item_serie_page_url, {}), "lxml")

    # fields contained in the item page
    obj_class_strong_elm = [x for x in item_page_soup.find_all('strong') if x.text.startswith('Object Class')][0]
    # print(obj_class_strong_elm.parent.text)
    obj_class = obj_class_strong_elm.parent.text.split('Object Class:')[-1].strip().lower()
    if obj_class[0] == ':':
        obj_class = obj_class[1:].strip()
    item_rate = int(item_page_soup.find('a', id='pagerate-button').text.split('(')[1].split(')')[0])
    item_comments = int(item_page_soup.find('a', id='discuss-button').text.split('(')[1].split(')')[0])
    item_tags = [x.text for x in item_page_soup.find('div', attrs={'class':'page-tags'}).find_all('a') if not x.text.startswith('_')]

    # title is contained in the serie page
    a_target = '/' + item_page_url.split('/')[-1]
    item_title = item_serie_page_soup.find('a', attrs={'href':a_target}).next.next[3:].strip()

    res = {
        'index': a_target[1:].upper(),
        'item_title': item_title,
        'url': item_page_url,
        'obj_class': obj_class,
        'item_rate': item_rate,
        'item_comments': item_comments,
        'item_tags': item_tags
    }
    return res

def insert_item(db_conn, idx):
    idx_s = get_scp_item_url(idx).split('/')[-1].upper()
    item_cnt = db_conn.execute("SELECT COUNT(*) from items where `Index` = '" + idx_s + "'").fetchall()[0][0]
    if item_cnt > 0:
        # the item is already in the database, skip.
        return
    itemdata = fetch_item(idx)
    assert itemdata['index'] == idx_s
    db_conn.execute("INSERT INTO items (`Index`, Title, URL, ObjectClass, Comments, Rating) VALUES (?, ?, ?, ?, ?, ?)", (idx_s, itemdata['item_title'], itemdata['url'], itemdata['obj_class'], itemdata['item_comments'], itemdata['item_rate']))
    item_id = db_conn.execute("SELECT Id from items where `Index` = '" + idx_s + "'").fetchall()[0][0]
    db_conn.commit()
    tags_newlines = [(item_id, t) for t in itemdata['item_tags']]
    db_conn.executemany("INSERT INTO itemtags (ItemId, TagName) VALUES (?, ?)", tags_newlines)
    db_conn.commit()

if __name__ == "__main__":
    db_conn = open_db()
    if db_conn is None:
        print("Failed to open db!")
        exit(1)

    banned_items = [1, 139]
    for idx in range(1, 201):
        if idx not in banned_items:
            insert_item(db_conn, idx)

    db_conn.close()
