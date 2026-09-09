from drf_spectacular.generators import SchemaGenerator


class TodayFixSchemaGenerator(SchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(
            request=request,
            public=public,
        )

        schema["info"]["title"] = "TodayFix Service API"

        return schema