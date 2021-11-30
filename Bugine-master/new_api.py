from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import RegexpTokenizer
from operator import itemgetter
from api import descript, query_issue, _filter_search_keys
from model import zip_handler, xml_parser, work_path, match_name, util, nlp_util, search_rank
from model import issuedb
import logging
import csv
from model import table2tsv
import time
import os
import sqlite3
import re
from nltk import ngrams

csv_path = "rank_result/"
stopWords = set(stopwords.words('english'))
stemmer = SnowballStemmer("english")

star_score = {"1": 3, "2": 2, "3": 1}  # ?


# tokenize, stopwords removal and stemming
def nlp_process(content: str) -> list:
    words_filtered = []
    tokenizer = RegexpTokenizer(r'\w+')
    result = tokenizer.tokenize(content)
    for w in result:
        w = w.lower()
        if w not in stopWords:
            if re.fullmatch("([A-Za-z0-9-'])\\w+", w) is not None:
                words_filtered.append(w)

    result = []
    for w in words_filtered:
        result.append(stemmer.stem(w))
    return result


def get_keywords() -> (dict, dict):
    hot_keywords = {}
    two_keywords = {}
    # get key words key = score
    with open('./model/conf/new_keywords.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            hot_keywords[row[0]] = float(row[1])
    f.close()
    with open('./model/conf/key_2_gram.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if float(row[1]) < 0.35:
                break
            two_keywords[row[0]] = float(row[1])
    # with open(work_path.in_project("./model/conf/hotkey.dat"), 'r', encoding='utf8') as f:
    #     for row in f.readlines():
    #         tmp = row.strip()
    #         if tmp != "":
    #             tmp = stemmer.stem(tmp)
    #             if tmp in m:
    #                 print(tmp)

    # z = open("./model/conf/new_keywords.csv", 'w', encoding='utf-8', newline='')
    # # # # 2. 基于文件对象构建 csv写入对象
    # csv_writer = csv.writer(z)
    # # # # 3. 构建列表头
    # # csv_writer.writerow(["word", "weight"])
    # hot_keywords = sorted(hot_keywords, key=itemgetter(1), reverse=True)
    # for h in hot_keywords:
    #     csv_writer.writerow(h)
    # z.close()
    return hot_keywords, two_keywords


def keywords_in_content(hot_keywords: dict, content_words: list, weight=False) -> int:
    # get key words key = score
    count_dict = {}
    for k in content_words:
        if k in hot_keywords:
            if k not in count_dict:
                if weight:
                    count_dict[k] = hot_keywords[k]  # 要不要给keywords加上分数呢？
                else:
                    count_dict[k] = 1
            elif weight:
                count_dict[k] += 1 * hot_keywords[k]  # 要不要给keywords加上分数呢？
            else:
                count_dict[k] += 1
    score = 0
    for k in count_dict:
        score += count_dict[k]
    return score


def ui_key_word(ui_keywords: set, content_words: list) -> int:
    count_dict = {}
    for k in ui_keywords:
        if k in content_words:
            if k not in count_dict:
                count_dict[k] = 10
            else:
                count_dict[k] += 10
    score = 0
    for k in count_dict:
        score += count_dict[k]
    return score


def rank_review(app_score_list: list, max_depth=4) -> list:
    hot_keywords, two_keywords = get_keywords()
    rdb = issuedb.ISSuedb()  
    all_review = []
    # number = [5000, 10000, 15000, 20000]
    # number = [1000, 2000, 3000, 4000]
    for m in range(min(len(app_score_list), max_depth)):
        score_list = app_score_list[m][2]
        app_weight = app_score_list[m][1]

        keys_sea = _filter_search_keys(score_list, threshold=0.7)
        ess_keys = set()
        for r in keys_sea:
            for a_list in r:
                ess_keys = ess_keys.union(a_list)
        ess_keys = " ".join(list(ess_keys))
        ess_keys = nlp_util.stem_sentence(ess_keys)
        ess_keys = set(ess_keys)
        app = app_score_list[m][0]
        app_name = os.path.basename(app)[:-4]
        score = {
            'star_num': 0,
            'hot_key_words': 0,
            'helpful_num': 0,
            'ui_key': 0,
            'similar_app': 0,  # app相似度
            'two_gram_keywords': 0,
        }
        sql = """select review_id,content,star_num,helpful_num from {} order by length(content) desc"""
        tab_name = table2tsv.file2table(app)  # csv -> 数据库名字
        output = rdb.db_retrieve(sql.format(tab_name))  # sql查询结果
        # head = ["review_id", "content", "bold", "star_num", "helpful_num", "reply_content"]
        head = ["review_id", "content", "star_num", "helpful_num"]
        f_output = issuedb.retrieve_formatter(head, output)
        # f_output[0].review_id
        for i in f_output:
            if len(i.content) < 100:
                break
            processed_content = nlp_process(i.content)  # 没有移除数字
            score_sum = 0
            score['star_num'] = star_score[i.star_num]
            score['hot_key_words'] = keywords_in_content(hot_keywords, processed_content, False) * app_weight  # 关键词计分
            score['ui_key_words'] = ui_key_word(ess_keys, processed_content) * app_weight
            # score['two_gram_keywords'] = two_gram_key_word(two_keywords, processed_content)
            score['helpful_num'] = int(i.helpful_num) * 0.25  # bug TypeError: can't multiply sequence by non-int of type 'float'
            if score['helpful_num'] > 25:
                score['helpful_num'] = 25
            for k in score:
                score_sum += score[k]
            if score_sum > 3:  # 3 2 1
                all_review.append([app_name, score_sum, i])
            # if len(all_review) > number[m]:
            #     break
    # 然后对all_review进行排序
    result = sorted(all_review, key=itemgetter(1), reverse=True)
    return result[:400]

def two_gram_key_word(two_keywords: dict, content_words: list, weight=False):
    ngrams2_li = [' '.join(w) for w in ngrams( content_words, 2)]
    count_dict = {}
    for k in ngrams2_li:
        if k in two_keywords:
            if k not in count_dict:
                count_dict[k] = 3
            else:
                count_dict[k] += 3
    score = 0
    for k in count_dict:
        score += count_dict[k]
    return score



if __name__ == '__main__':
    eee = "it.feio.android.omninotes"
    s = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime(time.time()))
    test = util.read_csv("model/data/description_extend_all/"+eee+".csv")
    print("begin search similar apps")
    scan_output = descript(test, source_category="Productivity",
                           except_files=eee,extend=True, pool_size=32)  # get similar app
    print("begin rank reviews")
    rank_result = rank_review(scan_output)
    print(util.get_col(scan_output, [0, 1]))
    now = time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime(time.time()))
    # 1. 创建文件对象
    z = open(csv_path +eee+ now + ".csv", 'w', encoding='utf-8', newline='')
    # # 2. 基于文件对象构建 csv写入对象
    csv_writer = csv.writer(z)
    # # 3. 构建列表头
    csv_writer.writerow(["app_id", "score", "star_num", "helpful_num", "review_content"])
    for i in rank_result:
        # # 写入文件
        csv_writer.writerow([i[0], i[1], i[2].star_num, i[2].helpful_num, i[2].content])
    # 5. 关闭文件
    z.close()
    print("end.")
    print(s)
    print(time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime(time.time())))
