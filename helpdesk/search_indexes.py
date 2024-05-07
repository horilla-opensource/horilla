from haystack import indexes

from .models import FAQ


class FAQIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    question = indexes.CharField(model_attr="question")
    answer = indexes.CharField(model_attr="answer")

    def get_model(self):
        return FAQ
