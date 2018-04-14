"""Dump a font's mark and mkmk feature"""
import logging

logger = logging.getLogger(__name__)


def mark_lookup_idxs(ttfont):
    for feat in ttfont['GPOS'].table.FeatureList.FeatureRecord:
        if feat.FeatureTag == 'mark':
            return feat.Feature.LookupListIndex
    return None


def base_anchors(glyph_list, anchors_list):
    glyphs = {}

    for glyph, anchors in zip(glyph_list, anchors_list):
        if glyph not in glyphs:
            glyphs[glyph] = {}
        for idx, anchor in enumerate(anchors.BaseAnchor):
            glyphs[glyph][idx] = {'name': glyph,
                                  'x': anchor.XCoordinate,
                                  'y': anchor.YCoordinate}
    return glyphs


def mark_anchors(glyph_list, anchors_list):
    glyphs = {}
    for glyph, anchor in zip(glyph_list, anchors_list):
        if anchor.Class not in glyphs:
            glyphs[anchor.Class] = []
        glyphs[anchor.Class].append({'name': glyph,
                                     'x': anchor.MarkAnchor.XCoordinate,
                                     'y': anchor.MarkAnchor.YCoordinate})

    return glyphs


def _flatten_format1_subtable(sub_table):
    base_glyphs = base_anchors(sub_table.BaseCoverage.glyphs,
                               sub_table.BaseArray.BaseRecord)
    mark_glyphs = mark_anchors(sub_table.MarkCoverage.glyphs,
                               sub_table.MarkArray.MarkRecord)

    table = []
    for base_glyph in base_glyphs:
        for anchor_class in base_glyphs[base_glyph]:

            for mark in mark_glyphs[anchor_class]:
                b_glyph = base_glyphs[base_glyph][anchor_class]
                m_glyph = mark

                table.append({
                    'base_glyph': b_glyph['name'],
                    'mark_glyph': m_glyph['name'],
                    'mark_x': m_glyph['x'],
                    'mark_y': m_glyph['y'],
                    'base_x': b_glyph['x'],
                    'base_y': b_glyph['y']
                })
    return table


def dump_marks(ttfont, glyph_map=None, ignore_metrics=True):
    """Return a list of base to mark anchor attachments

    :rtype: [
        {"base_glyph": glyph, "mark_glyph": glyph,
         'base_x': int, 'base_y':int,
         mark_x': int, mark_y: int,},

         {"base_glyph": glyph, "mark_glyph": glyph,
         'base_x': int, 'base_y':int,
         mark_x': int, mark_y: int,}
    ]

    if ignore_metrics is enabled. Every anchor's x coord will be normalised
    using the glyph's closest point in the x axis; instead of using the
    glyph's metrics.
    """
    if 'GPOS' not in ttfont.keys():
        logger.warning("Font doesn't have GPOS table. No marks found")
        return []
    gpos = ttfont['GPOS']
    lookup_idxs = mark_lookup_idxs(ttfont)
    if not lookup_idxs:
        logger.warning("Font doesn't have a GPOS mark feature")
        return []

    table = []
    for idx in lookup_idxs:
        lookup = gpos.table.LookupList.Lookup[idx]

        for sub_table in lookup.SubTable:
            if sub_table.Format == 1 and sub_table.LookupType == 4:
                table += _flatten_format1_subtable(sub_table)
            # TODO (M Foley) add LookupType 5 marks to lig

    if ignore_metrics:
        metrics = ttfont['hmtx'].metrics
        glyf = ttfont['glyf']
        for mark in table:
            mark['base_x'] = metrics[mark['base_glyph']][1] - mark['base_x']
            mark['mark_x'] = metrics[mark['mark_glyph']][1] - mark['mark_x']

            mark['base_y'] = glyf[mark['base_glyph']].yMin - mark['base_y']
            mark['mark_y'] = glyf[mark['mark_glyph']].yMin - mark['mark_y']

    if glyph_map:
        for row in table:
            row['base_glyph'] = glyph_map[row['base_glyph']]
            row['mark_glyph'] = glyph_map[row['mark_glyph']]
    return table
