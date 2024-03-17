import re
from typing import Iterable
import logging

logger = logging.getLogger(__name__)

def split_list(l, n):
    k, m = divmod(len(l), n)
    return (l[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n))


def split_list_into_chunks_of_size_n(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def split_keywords(keywords_string: str) -> list:
    words = []
    l = keywords_string.split(";")
    for w in l:
        if w == "" or w == " ":
            continue

        if "," in w:
            for i in w.split(","):
                if i == "" or i == " ":
                    continue
                else:
                    words.append(i)
        else:
            words.append(w)
    words = [word.strip() for word in words]
    return words


def split_keywords_on_slash(keywords_string: str) -> list:
    words = keywords_string.split("/")
    iter_words = iter(words)
    final_words = []
    for i, w in enumerate(iter_words):
        if w[-2] == " " and w[-1].isalnum() and i < len(words) - 1:
            united_word = "/".join([w, words[i + 1]])

            final_words.append(united_word)
            next(iter_words)
            continue
        else:
            final_words.append(w)
    return final_words


def remove_latin_characters(words_list: list) -> list:
    updated_words = []
    for word in words_list:
        updated_word = re.sub(r"[a-zA-Z]", "", word).strip()
        if updated_word:
            updated_words.append(updated_word)
    return updated_words


def remove_duplicates_from_list(words_list) -> list:
    return list(set(words_list))


def mean(lst: list) -> float:
    return round(sum(lst) / len(lst), 2)


def convert_ozon_datetime_str_to_odoo_datetime_str(ozon_datetime_str: str):
    return ozon_datetime_str.replace("T", " ").replace("Z", "")


def delete_records(model: str, ids: Iterable, env):
    if ids:
        query = f"DELETE FROM {model} WHERE id IN %s"
        env.cr.execute(query, (tuple(ids),))
        logger.warning(f"delete from {model} records with ids {ids}")


def direct_update(model: str, id_: int, vals: dict, env):
    vals_to_str = ', '.join([f"{key} = %s" for key, value in vals.items()])
    query = f"UPDATE {model} SET {vals_to_str} WHERE id = %s"
    params = [value if isinstance(value, bytes) else str(value) for value in vals.values()]
    params.append(id_)

    env.cr.execute(query, tuple(params))
    env.cr.commit()
