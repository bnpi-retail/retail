import re


def split_list(l, n):
    k, m = divmod(len(l), n)
    return (l[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n))


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
