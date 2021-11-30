# 对于Bugine的一些理解

![bugine-simple](Automatic-testing\bugine-simple.png)

Bugine分为三个部分。预处理，提取应用程序描述文件，排序。

首先是对Github问题的收集以及元数据处理。他建立了一个github问题的数据库，他将找到的问题先经过一些筛选，再通过/model/nlp_util文件对其进行自然语言处理。再通过/model/xml_parser进行xml文件的预处理，去除那些没有意义的词，留下有意义的词汇。

再是提取应用程序描述文件。他通过match_name来将获取到的关键词进行匹配并计算它们的相似度，其中的ngram_compare（）方法即是用来衡量Github问题和测试题之间的相似度的。

最后是进行排序。这主要靠map_issue和search_rank完成。我们使用从应用程序描述文件中提取的每个查询短语来搜索相关问题，并根据其重要性、相关性和再现性对结果进行排序。他先计算hit _all hit_overlap等度量，在计算权重后运用calc_candidate_seq（）方法对其进行相应的排序