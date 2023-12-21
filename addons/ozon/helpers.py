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
