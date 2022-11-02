from app.objects.secondclass.c_link import LinkSchema


import marshmallow as ma
from marshmallow import fields


class LinkResultSchema(ma.Schema):
    link = fields.Nested(LinkSchema(partial=True))
    result = fields.String()
