from rest_framework import relations
from rest_framework.utils.urls import replace_query_param

__all__ = [
    "ContextHyperlinkedIdentityField",
]


class ContextHyperlinkedIdentityField(relations.HyperlinkedIdentityField):
    def __init__(self, *args, **kwargs):
        # pop the `context_params` from the kwargs and default to an
        # empty tuple if these `context_params` are not part of the kwargs.
        self._context_params = kwargs.pop("context_params", tuple())

        super().__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, "pk") and obj.pk in (None, ""):
            return None

        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {self.lookup_url_kwarg: lookup_value}
        url = self.reverse(view_name, kwargs=kwargs, request=request, format=format)

        # add the `context_params` to the url
        for context_param in self._context_params:
            if context_param and (context_param in request.GET):
                value = request.GET[context_param]
                url = replace_query_param(url, context_param, value)

        return url
