from django.views.generic import TemplateView, ListView
from typing import Any, Dict
from django.utils.safestring import mark_safe
from django.db.models.query import QuerySet
from django.db.models import Q
import operator

from .models import Transcript


class HomePageView(TemplateView):
    template_name = 'home.html'


class SearchResultsView(ListView):
    model = Transcript
    template_name = 'search_results.html'
    context_object_name = 'episode_list'
    paginate_by = 3

    def get_queryset(self) -> QuerySet:
        ''' Get Transcript objects containing query in text filed

        Returns
        -------
        QuerySet
            transcript objects containing query in text filed

        '''
        self.query = self.request.GET.get('q')
        splitted = self.query.split(' ')

        q = [Q(text__icontains=splitted[i]) for i in range(len(splitted))]

        if len(q) == 1:
            self.episode_list = Transcript.objects.filter(
                text__icontains=self.query)
        elif len(q) == 2:
            c0, c1 = [i for i in q]
            self.episode_list = Transcript.objects.filter(
                c0, c1)
        elif len(q) == 3:
            c0, c1, c2 = [i for i in q]
            self.episode_list = Transcript.objects.filter(
                c0, c1, c2)
        elif len(q) == 4:
            c0, c1, c2, c3 = [i for i in q]
            self.episode_list = Transcript.objects.filter(
                c0, c1, c2, c3)
        elif len(q) == 5:
            c0, c1, c2, c3, c4 = [i for i in q]
            self.episode_list = Transcript.objects.filter(
                c0, c1, c2, c3, c4)
        elif len(q) == 6:
            c0, c1, c2, c3, c4, c5 = [i for i in q]
            self.episode_list = Transcript.objects.filter(
                c0, c1, c2, c3, c4, c5)
        elif len(q) == 7:
            c0, c1, c2, c3, c4, c5, c6 = [
                i for i in q]
            self.episode_list = Transcript.objects.filter(
                c0, c1, c2, c3, c4, c5, c6)
        else:
            c0, c1, c2, c3, c4, c5, c6, *_ = [
                i for i in q]
            self.episode_list = Transcript.objects.filter(
                c0, c1, c2, c3, c4, c5, c6)

        return self.episode_list

    def get_context_data(
            self,
            **kwargs: Any) -> Dict[str, Any]:
        ''' Update context_data to be used in html

        Returns
        -------
        Dict[str, Any]
            updated context_data

        '''
        context = super(SearchResultsView, self).get_context_data(**kwargs)
        context['count'] = self.count_total()
        episode_list = context['episode_list']
        # transcripts_list = self.highlight()
        each_query_count = self.get_exact_match().values()
        short_texts = self.get_short_text_highlighted()

        episodes_and_transcripts = self.sort_by_occurrence_descending(
            each_query_count,
            episode_list,
            short_texts)

        context['ep_countq_trans'] = episodes_and_transcripts
        context['query'] = self.query
        # self.get_each_word_in_query_count()
        return context

    def sort_by_occurrence_descending(
            self,
            each_query_count,
            episode_list,
            short_texts):
        unsorted = zip(
            each_query_count, episode_list, short_texts)
        zipped = list(unsorted)
        episodes_and_transcripts = reversed(
            sorted(zipped, key=operator.itemgetter(0)))
        return episodes_and_transcripts

    def get_short_text_highlighted(self):
        short_texts = []
        for episode in self.episode_list:
            text = episode.text.lower()
            index = text.find(self.query.lower())
            idx_query_word = index + len(self.query)
            around_idx = 200

            start_idx = index - around_idx
            end_idx = around_idx + idx_query_word
            first_char_idx = self.prepend_beginning_of_string(text, start_idx)
            last_char_idx = self.append_end_of_string(text, end_idx)

            short_text = text[first_char_idx:last_char_idx]

            replacing_query = '<span class="highlighted"><strong>{}</strong></span>'.format(
                self.query)
            short_text_highlighted = short_text.replace(
                self.query.lower(), replacing_query)

            # the edge case where the query is at the beginning
            # of the transcript
            if first_char_idx != 0:
                short_text_highlighted = '(...) ' + short_text_highlighted

            # the edge case where the query is at the end of the transcript
            if last_char_idx != len(text):
                short_text_highlighted += '(...)'
            short_text_highlighted = mark_safe(short_text_highlighted)
            short_texts.append(short_text_highlighted)
        return short_texts

    def append_end_of_string(self, text, end_idx):
        better_idx = 0

        # the edge case where the query is at the end of the transcript
        if end_idx + better_idx > len(text):
            return(len(text))

        while text[end_idx+better_idx] != ' ':
            better_idx += 1
        return better_idx + end_idx

    def prepend_beginning_of_string(self, text, start_idx):
        better_idx = 0
        while text[start_idx-better_idx] != ' ':
            better_idx -= 1

        # the edge case where the query is at the beginning of the transcript
        if start_idx - better_idx < 0:
            return 0
        return start_idx - better_idx

    def count_total(self) -> str:
        ''' Count how many times a given query appears in database in total
        (only text attribute) in how many distinct episodes

        Returns
        -------
        str
            text with info about how many queries appears in database
            e.g.
            'Found 37 occurrences of "world" in 2 episodes in total'

        '''
        each_query_count = self.get_each_word_in_query_count()
        print(each_query_count)
        # print(each_query_count.keys())
        total_episodes = len(each_query_count.keys())
        # print(total_episodes)
        queries_sum = self.get_queries_sum()
        print(queries_sum)
        # total_queries = sum(each_query_count.values())
        total_queries = sum(queries_sum.values())
        # print(total_queries)
        ep_form = 'episode'
        if total_episodes > 1:
            ep_form = 'episodes'
        response = 'Found {} occurrences of "{}" in {} {} in total'.format(
            total_queries, self.query, total_episodes, ep_form)

        return response

    def get_queries_sum(self):
        queries_sum = {}
        each_query_count = self.get_each_word_in_query_count()
        for episode_number, inner_dict in each_query_count.items():
            total_queries_count = 0
            for occurence in inner_dict.values():
                total_queries_count += int(occurence)
                queries_sum[episode_number] = total_queries_count
        return queries_sum

    def get_exact_match(self) -> Dict[str, int]:
        '''Get dict with info about how any occurrences of a given query
        appears per episode

        Returns
        -------
        Dict[str, int]
            e.g.

            >>> each_query_count = {'815': 2, '816': 35}

        '''
        count = 0
        exact_match = {}
        for episode in self.episode_list:
            count = episode.text.lower().count(self.query.lower())
            exact_match[episode.episode_number] = count
        return exact_match

    def get_each_word_in_query_count(self):
        count = 0
        each_query_count = {}
        for episode in self.episode_list:
            inner_dict = {}
            for word in self.query.split(' '):
                count = episode.text.lower().count(word.lower())
                inner_dict[word] = count
            each_query_count[episode.episode_number] = inner_dict
        return each_query_count


class TranscriptView(ListView):
    model = Transcript
    template_name = 'transcript.html'
    context_object_name = 'episode_list'

    def get_context_data(self, **kwargs):
        context = super(TranscriptView, self).get_context_data(**kwargs)
        self.query = self.kwargs['query']
        episode_number = self.kwargs['episode_number']
        context['episode_number'] = episode_number
        element = Transcript.objects.filter(pk=episode_number)

        # element[0] because element is a list of one element
        text = mark_safe(element[0].text)
        highlighted_text = self.get_highlighted_text(text)
        context['highlighted_text'] = highlighted_text
        context['query'] = self.query
        return context

    def get_highlighted_text(
            self,
            text,
            **kwargs) -> str:
        ''' Highlight query in transcript text

        Returns
        -------
        highlighted_text : str
            Formated transcript with html tags that displays hightlights while
            rendering

        '''
        import re
        replacing_query = '<span class="highlighted"><strong>{}</strong></span>'.format(
            self.query.upper())
        insensitive_query = re.compile(
            re.escape(str(self.query)), re.IGNORECASE)
        insensitive_text = insensitive_query.sub(replacing_query, text)
        highlighted_text = mark_safe(insensitive_text)
        return highlighted_text


class TranscriptPlainView(ListView):
    model = Transcript
    template_name = 'transcript_plain.html'
    # context_object_name = 'episode'

    def get_context_data(self, **kwargs):
        context = super(TranscriptPlainView, self).get_context_data(**kwargs)
        self.query = self.kwargs['query']
        episode_number = self.kwargs['episode_number']
        context['episode_number'] = episode_number
        element = Transcript.objects.filter(pk=episode_number)
        context['episode'] = element[0]
        # context['text'] = text
        # element[0] because element is a list of one element
        context['query'] = self.query
        return context
