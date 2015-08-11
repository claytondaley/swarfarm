from rest_framework import viewsets, filters, status, renderers
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from rest_framework_extensions.cache.decorators import cache_response
from django.shortcuts import get_object_or_404

from herders.models import Monster, MonsterSkill, MonsterSkillEffect, MonsterLeaderSkill, MonsterSource, \
    Summoner, MonsterInstance, RuneInstance, TeamGroup, Team
from .serializers import MonsterSerializer, MonsterSummarySerializer, MonsterSkillSerializer, MonsterLeaderSkillSerializer, MonsterSkillEffectSerializer, MonsterSourceSerializer, \
    SummonerSerializer, MonsterInstanceSerializer, RuneInstanceSerializer, TeamGroupSerializer, TeamSerializer


# Pagination classes
class PersonalCollectionSetPagination(PageNumberPagination):
    page_size = 1000


class BestiarySetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 1000


# Django REST framework views
class MonsterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Monster.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer, renderers.TemplateHTMLRenderer)

    pagination_class = BestiarySetPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('element', 'archetype', 'base_stars', 'obtainable', 'is_awakened')

    def get_serializer_class(self):
        if self.action == 'list':
            return MonsterSummarySerializer
        else:
            return MonsterSerializer

    @cache_response(6 * 60 * 60, cache_errors=False)
    def list(self, request, *args, **kwargs):
        response = super(MonsterViewSet, self).list(request, *args, **kwargs)

        if request.accepted_renderer.format == 'html':
            return Response({'data': response.data['results']}, template_name='api/bestiary/table_rows.html')
        return response

    # @cache_response(1 * 60 * 60, cache_errors=False)
    def retrieve(self, request, *args, **kwargs):
        response = super(MonsterViewSet, self).retrieve(request, *args, **kwargs)

        if request.accepted_renderer.format == 'html':
            return Response({'monster': response.data}, template_name='api/bestiary/detail.html')
        return response


class MonsterSkillViewSet(CacheResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MonsterSkill.objects.all()
    serializer_class = MonsterSkillSerializer
    pagination_class = BestiarySetPagination


class MonsterLeaderSkillViewSet(CacheResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MonsterLeaderSkill.objects.all()
    serializer_class = MonsterLeaderSkillSerializer
    pagination_class = BestiarySetPagination


class MonsterSkillEffectViewSet(CacheResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MonsterSkillEffect.objects.all()
    serializer_class = MonsterSkillEffectSerializer
    pagination_class = BestiarySetPagination


class MonsterSourceViewSet(CacheResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MonsterSource.objects.all()
    serializer_class = MonsterSourceSerializer
    pagination_class = BestiarySetPagination


class SummonerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Summoner.objects.filter(public=True)
    serializer_class = SummonerSerializer


class MonsterInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MonsterInstance.objects.none()
    serializer_class = MonsterInstanceSerializer
    pagination_class = PersonalCollectionSetPagination

    def get_queryset(self):
        profile_name = self.kwargs.get('profile_name', None)
        instance_id = self.kwargs.get('instance_id', None)

        if profile_name:
            summoner = get_object_or_404(Summoner, user__username=profile_name)
            is_owner = (self.request.user.is_authenticated() and summoner.user == self.request.user)

            if is_owner or summoner.public:
                if instance_id:
                    # Return single monster
                    return get_object_or_404(MonsterInstance, pk=instance_id)
                else:
                    # Return list of monsters owned
                    return MonsterInstance.objects.filter(owner=summoner)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class RuneInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RuneInstance.objects.all()
    serializer_class = RuneInstanceSerializer
    pagination_class = PersonalCollectionSetPagination


class TeamGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TeamGroup.objects.all()
    serializer_class = TeamGroupSerializer
    pagination_class = PersonalCollectionSetPagination


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    pagination_class = PersonalCollectionSetPagination
