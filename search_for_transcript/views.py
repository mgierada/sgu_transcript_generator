from django.views.generic import TemplateView, ListView
from typing import Any, Dict, List
from django.utils.safestring import mark_safe
from django.db.models.query import QuerySet
from django.db.models import Q
from django.core.paginator import Paginator
import re
import operator
from .utils import forbiden_words

from .models import Transcript


class HomePageView(TemplateView):
    template_name = 'home.html'


class SearchResultsView(ListView):
    model = Transcript
    template_name = 'search_results.html'
    context_object_name = 'episode_list'
    paginate_idx = 3

    def get_queryset(self) -> QuerySet:
        ''' Get Transcript objects containing query in text filed

        Returns
        -------
        QuerySet
            transcript objects containing query in text filed

        '''
        self.unmodified_query = self.request.GET.get('q').lower()

        # check if exact match execution can be started
        if self.is_exact_match_requested():
            self.get_exact_match()
        else:
            self.get_partial_match()

    def is_exact_match_requested(self):
        if (
            self.unmodified_query[0] == "\""
            and
            self.unmodified_query[len(self.unmodified_query) - 1] == "\""
        ):
            return True
        return False

    def get_exact_match(self):
        self.query = self.unmodified_query[1:-1]
        self.episode_list = Transcript.objects.filter(
            text__icontains=self.query)
        return self.episode_list

    def get_partial_match(self):
        splitted_query = self.unmodified_query.split(' ')
        self.query = self.check_for_forbidden_words(splitted_query)

        q = [Q(text__icontains=splitted_query[i])
             for i in range(len(splitted_query))]

        # that if-else statement is a nasty part of the code #TODO refactor it
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

    def check_for_forbidden_words(self, splitted_query):
        splitted_query_cleaned = [
            word for word in splitted_query if word not in forbiden_words]
        return ' '.join(splitted_query_cleaned)

    def get_context_data(
            self,
            **kwargs: Any) -> Dict[str, Any]:
        ''' Update context_data to be used in html template

        Returns
        -------
        Dict[str, Any]
            updated context_data

        '''
        if self.is_exact_match_requested():
            return self.get_context_data_exact_match(**kwargs)
        else:
            return self.get_context_data_partial_match(**kwargs)

    def get_context_data_exact_match(
            self,
            **kwargs: Any) -> Dict[str, Any]:
        context = super(SearchResultsView, self).get_context_data(**kwargs)
        self.short_texts_list = self.get_short_text_highlighted()

    def get_context_data_partial_match(
            self,
            **kwargs: Any) -> Dict[str, Any]:
        context = super(SearchResultsView, self).get_context_data(**kwargs)
        self.each_query_count_list = list(self.get_queries_sum().values())
        self.short_texts_list = self.get_short_text_highlighted()

        # sort queries, episodes_list and transcritps by query occurrence
        sorted_q_e_st = self.sort_by_occurrence_descending()

        # unzip sorted list
        q_sorted, e_sorted, st_sorted = zip(
            *sorted_q_e_st)

        paginator_q = Paginator(q_sorted, self.paginate_idx)
        page_q = self.request.GET.get('page')
        page_obj_q = paginator_q.get_page(page_q)

        paginator_e = Paginator(e_sorted, self.paginate_idx)
        page_e = self.request.GET.get('page')
        page_obj_e = paginator_e.get_page(page_e)

        paginator_st = Paginator(st_sorted, self.paginate_idx)
        page_st = self.request.GET.get('page')
        page_obj_st = paginator_st.get_page(page_st)

        # zip the final and sorted objects and add it to context
        q_e_st_paginated = zip(
            page_obj_q, page_obj_e, page_obj_st)
        context['queries_episodes_short_texts'] = q_e_st_paginated

        # update page_obj as it is manually edited
        context['paginator'] = paginator_q
        context['page_obj'] = page_obj_q
        context['is_paginated'] = True

        # add other usefull variables
        context['query'] = self.query
        context['initial_query'] = self.unmodified_query
        context['count'] = self.count_total()

        # print(self.get_exact_match())
        return context

    def sort_by_occurrence_descending(self) -> List[object]:
        ''' Sort queries count, episodes and short text together by decending
        occurrence of query

        Returns
        -------
        List[object]
            a reversed list iterator (zip) holding sorted
            queries count, episodes and short texts

        '''
        unsorted = zip(
            self.each_query_count_list,
            self.episode_list,
            self.short_texts_list)
        zipped = list(unsorted)
        sorted_q_e_st = reversed(
            sorted(zipped, key=operator.itemgetter(0)))
        return sorted_q_e_st

    def get_index_dict_first_occurence(self):
        index_dict = {}
        for episode in self.episode_list:
            inner_dict = {}
            for word in self.query.split(' '):
                text = episode.text.lower()
                index = text.find(word.lower())
                idx_query_word = index + len(word)
                inner_dict[word] = idx_query_word
            index_dict[episode.episode_number] = inner_dict
        return index_dict

    def get_lowest_idx(self):
        index_dict = self.get_index_dict_first_occurence()
        pass

    def get_most_common_query_word(self, episode_number):
        for word, occurance in self.each_query_count[episode_number].items():
            if occurance == max(self.each_query_count[episode_number].values()):
                return word

    def get_short_text_highlighted(self, around_idx=200):
        short_texts = []
        self.each_query_count = self.get_each_word_in_query_count()

        for episode in self.episode_list:
            if self.is_exact_match_requested():
                most_common_word = self.query
            else:
                most_common_word = self.get_most_common_query_word(
                    episode.episode_number)
            # text = episode.text.lower()
            text = episode.text

            index, _ = re.search(most_common_word, text, re.IGNORECASE).span()
            idx_query_word = index + len(most_common_word)
            start_idx = index - around_idx
            end_idx = around_idx + idx_query_word

            first_char_idx = self.prepend_beginning_of_string(text, start_idx)
            last_char_idx = self.append_end_of_string(text, end_idx)

            short_text = text[first_char_idx:last_char_idx]

            # highlight all query words

            if self.is_exact_match_requested():
                replacing_query = '<span class="highlighted"><strong>{}</strong></span>'.format(
                    self.query)
                insensitive_query = re.compile(
                    re.escape(str(self.query)), re.IGNORECASE)
                insensitive_text = insensitive_query.sub(
                    replacing_query, short_text)
                short_text = insensitive_text
                short_text_highlighted = short_text
            else:
                for word in self.query.split(' '):
                    replacing_query = '<span class="highlighted"><strong>{}</strong></span>'.format(
                        word)
                    insensitive_query = re.compile(
                        re.escape(str(word)), re.IGNORECASE)
                    insensitive_text = insensitive_query.sub(
                        replacing_query, short_text)
                    short_text = insensitive_text
                short_text_highlighted = short_text

            # the edge case where the query is at the beginning
            # of the transcript
            if first_char_idx != 0:
                short_text_highlighted = '(...) ' + short_text_highlighted

            # the edge case where the query is at the end of the transcript
            if last_char_idx != len(text):
                short_text_highlighted += ' (...)'
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
        total_episodes = len(each_query_count.keys())
        queries_sum = self.get_queries_sum()
        total_queries = sum(queries_sum.values())
        ep_form = 'episode'
        self.get_formatted_query()
        if total_episodes > 1:
            ep_form = 'episodes'
        formatted_query = self.get_formatted_query()
        response = 'Found {} occurrences of {} in {} {} in total'.format(
            total_queries, formatted_query, total_episodes, ep_form)

        return response

    def get_formatted_query(self) -> str:
        ''' Split query to each word and add ""

        Returns
        -------
        str
            a formatted query with ""
            e.g.
            >>> self.query = 'covid vaccine usa'
            >>> self.get_formatted_query()
            >>> "covid" "vaccine" "usa"

        '''
        splitted_query = self.query.split(' ')
        formatted_query_string = ''
        for q in splitted_query:
            formatted = '"{}" '.format(q)
            formatted_query_string += formatted
        return formatted_query_string

    def get_queries_sum(self) -> Dict[int, int]:
        ''' Get a dict showing how many occurance of all words in query
        are there per episode

        Returns
        -------
        Dict[int, int]
            a dict like that
            >>> query = 'covid vaccine usa'

            >>> queries_sum = {790: 34, 551: 14}

        '''
        queries_sum = {}
        each_query_count = self.get_each_word_in_query_count()
        for episode_number, inner_dict in each_query_count.items():
            total_queries_count = 0
            for occurence in inner_dict.values():
                total_queries_count += int(occurence)
                queries_sum[episode_number] = total_queries_count
        return queries_sum

    def get_exact_match_dict(self) -> Dict[str, int]:
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
            count = episode.text.count(self.query)
            exact_match[episode.episode_number] = count
        return exact_match

    def get_each_word_in_query_count(self) -> Dict[int, Dict[str, int]]:
        ''' Get a dictionary showing how many times given word in query
        occures per episode

        Returns
        -------
        Dict[int, Dict[str, int]]
            a dict like that
            e.g.

            >>> query = 'covid vaccine usa'

            >>> each_query_count =
            {
                790:
                    {'covid': 10, 'vaccine': 5, 'usa': 19},
                551:
                    {'covid': 1, 'vaccine': 6, 'usa': 7}
            }

        '''
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
        self.element = Transcript.objects.filter(pk=episode_number)

        # element[0] because element is a list of one element
        text = (self.element[0].text)
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
        splitted_list = self.query.split(' ')[1:]

        for word in splitted_list:
            replacing_query = '<span class="highlighted"><strong>{}</strong></span>'.format(
                word.upper())
            insensitive_query = re.compile(
                re.escape(str(word)), re.IGNORECASE)
            insensitive_text = insensitive_query.sub(replacing_query, text)
            text = insensitive_text
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
