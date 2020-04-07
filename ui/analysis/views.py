from django.http import HttpResponse
from analyze import analyze
from django.shortcuts import render
from django import forms
import visualize
from django_pandas.managers import DataFrameManager
import pandas
import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt; plt.rcdefaults()
matplotlib.use('TkAgg')


# Create your views here.

NETWORK = [("CNN", "CNN"), ("Fox", "Fox"), ("MSNBC", "MSNBC")]

def summary(request):

    return render(request, 'summary-report.html')

def about(request):

    return render(request, 'about.html')


def index(request):

    context = {}
    res = None
    query = False
    args = None
    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
           #convert form data to arguments
            args = {}
            speaker_name = form.cleaned_data['speaker_name']
            if speaker_name:
                args['speaker_name'] = speaker_name
            speaker_title = form.cleaned_data['speaker_title']
            if speaker_title:
                args['speaker_title'] = speaker_title
            network_name = form.cleaned_data['network_name']
            if network_name:
                args['network_name'] = network_name
            show_name = form.cleaned_data['show_name']
            if show_name:
                args['show_name'] = show_name
            term = form.cleaned_data['term'].split()
            if term:
                args['term'] = term
            try:
                res = visualize.retrieve_data(args)
                query = True
            except Exception as e:
                print('Exception caught')
                bt = traceback.format_exception(*sys.exc_info()[:3])
                context['err'] = """
                An exception was thrown in find_courses:
                <pre>{}
{}</pre>
                """.format(e, '\n'.join(bt))

    else:
        form = SearchForm()
    context['form'] = form
    context['query'] = query
    context['args'] = args
    if args and res is not None and not res.empty:
        context['most_salient'] = analyze(res)
        visualize.speaker_summary(res)



    return render(request, 'index.html', context)


class SearchForm(forms.Form):
    speaker_name = forms.CharField(label='Speaker Name', max_length=100,
                                   required=True)
    speaker_title = forms.CharField(label='Speaker Title', max_length=100,
                                    required=False)
    network_name = forms.MultipleChoiceField(label="Network", choices=NETWORK,
                                        widget=forms.CheckboxSelectMultiple,
                                        required=False) 
    show_name = forms.CharField(label="Show Name", max_length=50,
                                required=False)
    term = forms.CharField(label="Keywords", max_length=150, required=False)