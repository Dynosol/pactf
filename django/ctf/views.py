import inspect

from django.contrib.auth.decorators import (login_required as _login_required,
                                            permission_required as _permission_required)
from django.http.response import HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import render, render_to_response, redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import DetailView
from django.conf import settings

from . import models
from .constants import COMPETE_PERMISSION_CODENAME


# region Helpers

# FIXME(Yatharth): Don't just check if user exists but that user's competitor's team exists

# FIXME(Yatharth): Use this in all views
def get_default_dict(request):
    result = {}
    result['production'] = not settings.DEBUG
    if request.user.is_authenticated() and request.user.has_perm(COMPETE_PERMISSION_CODENAME):
        result['team'] = request.user.competitor.team
    else:
        result['team'] = None
    return result


def decorate_classes(methodname):
    """Decorates a decorator to be able to decorate both a function and a certain method of a class

    Don't call the decorated decorator without arguments (pass nothing if you must). For help, contact Yatharth."""

    def meta_decorator_factory(old_decorator_factory):

        def new_decorator_factory(*args, **kwargs):
            old_decorator = old_decorator_factory(*args, **kwargs)

            def new_decorator(view):
                if inspect.isclass(view):
                    decorator = method_decorator(old_decorator, methodname)
                else:
                    decorator = old_decorator
                return decorator(view)

            return new_decorator

        return new_decorator_factory

    return meta_decorator_factory


login_required = decorate_classes('dispatch')(_login_required)
permission_required = decorate_classes('dispatch')(_permission_required)


@decorate_classes(methodname='get')
def http_method(method):
    """Decorates views to check for HTTP method"""

    assert method in ('GET', 'POST', 'PUT', 'DELETE')
    # TODO(Yatharth): Show custom page per http://stackoverflow.com/questions/4614294
    error = HttpResponseNotAllowed('Only {} requests allowed here'.format(method))

    def decorator(view):
        def decorated(request, *args, **kwargs):
            if request.method != method:
                return error
            return view(request, *args, **kwargs)

        return decorated

    return decorator


# endregion


# region GETs

@http_method('GET')
def index(request):
    return render(request, 'ctf/index.html', get_default_dict(request))


@permission_required(COMPETE_PERMISSION_CODENAME)
@http_method('GET')
def game(request):
    params = get_default_dict(request)
    params['prob_list'] = models.CtfProblem.objects.all
    params['team'] = request.user.competitor.team
    return render(request, 'ctf/game.html', params)


@http_method('GET')
class Team(DetailView):
    model = models.Team
    template_name = 'ctf/team.html'

    def get_context_data(self, **kwargs):
        context = super(Team, self).get_context_data(**kwargs)
        context.update(get_default_dict(self.request))
        return context


# @permission_required(COMPETE_PERMISSION_CODENAME)
@login_required()
@http_method('GET')
class CurrentTeam(Team):
    def get_object(self):
        return self.request.user.competitor.team


# endregion


# region POSTs

@http_method('POST')
def register(request, handle, passwd):
    pass


# @permission_required(COMPETE_PERMISSION_CODENAME)
@http_method('POST')
def submit_flag(request, problem_id):
    # TODO(Yatharth): Disable form submission if problem has already been solved (and add to Feature List)
    # TODO(Cam): React if the team has already solved the problem

    flag = request.POST.get('flag', '')
    # FIXME(Cam): Calculate user and team from session

    competitor = request.user.competitor
    team = competitor.team

    try:
        problem = models.CtfProblem.objects.get(id=problem_id)
    except models.CtfProblem.DoesNotExist:
        return HttpResponseNotFound("Problem with id {} not found".format(problem_id))
    else:
        if models.Submission.objects.filter(p_id=problem_id, team=team, correct=True):
            messager = messages.error
            message = "Your team has already solved this problem!"
        elif models.Submission.objects.filter(p_id=problem_id, team=team, flag=flag):
            messager = messages.error
            message = "You or someone on your team has already tried this flag!"
        else:
            correct, message = problem.grade(flag)
            if correct:
                messager = messages.success
                team.score += problem.points
                team.save()
            else:
                messager = messages.error
        s = models.Submission(p_id=problem_id, user=competitor, flag=flag, correct=correct)
        s.save()
        messager(request, message)
        return redirect('ctf:game')

# endregion
