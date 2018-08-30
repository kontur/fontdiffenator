from fontTools.varLib.mutator import instantiateVariableFont
import os

comp_order = [
    'attribs',
    'names',
    'glyphs',
    'metrics',
    'marks',
    'mkmk',
    'kerns'
]

column_mapping = {
    ('attribs', 'modified'): ['table', 'attrib', 'value_a', 'value_b'],

    ('metrics', 'modified'): ['glyph', 'diff_adv', 'diff_lsb', 'diff_rsb'],

    ('kerns', 'modified'): ['left', 'right', 'diff'],
    ('kerns', 'new'): ['left', 'right', 'value'],
    ('kerns', 'missing'): ['left', 'right', 'value'],

    ('marks', 'modified'): ['base_glyph', 'mark_glyph', 'diff_x', 'diff_y'],
    ('marks', 'new'): ['base_glyph', 'mark_glyph', 'base_x',
                       'base_y', 'mark_x', 'mark_y'],
    ('marks', 'missing'): ['base_glyph', 'mark_glyph', 'base_x',
                           'base_y', 'mark_x', 'mark_y'],

    ('mkmks', 'modified'): ['base_glyph', 'mark_glyph', 'diff_x', 'diff_y'],
    ('mkmks', 'new'): ['base_glyph', 'mark_glyph', 'base_x',
                       'base_y', 'mark_x', 'mark_y'],
    ('mkmks', 'missing'): ['base_glyph', 'mark_glyph', 'base_x',
                           'base_y', 'mark_x', 'mark_y'],

    ('glyphs', 'modified'): ['glyph', 'diff'],
    ('glyphs', 'new'): ['glyph'],
    ('glyphs', 'missing'): ['glyph'],

    ('names', 'modified'): ['id', 'string_a', 'string_b'],
    ('names', 'new'): ['id', 'string'],
    ('names', 'missing'): ['id', 'string'],
}


def dict_table(l, columns=None, clip_col=False, markdown=False):
    """Output a cli friendly table from a list of dicts"""
    table = []
    if not columns:
        columns = l[0].keys()
    # create table header
    if markdown:
        table += [
            '\n',
            ' | '.join(columns),
            '--- | ' * len(columns)
        ]
    else:
        t_format = unicode("{:<20}" * len(columns))
        header = t_format.format(*tuple(columns))
        table.append(header)

    for row in l:
        if markdown:
            table.append(_assemble_markdown_row(row, columns))
        else:
            table.append(
                _assemble_cli_row(t_format, row, columns, clip_col=clip_col)
            )
    return '\n'.join(table)


def _assemble_markdown_row(row, columns):
    assembled = []
    for h in columns:
        cell = unicode(row[h])
        assembled.append(cell)
    return ' | '.join(assembled)


def _assemble_cli_row(t_format, row, columns, clip_col=False):
    """Output a clie friendly table from a list of dicts"""
    assembled = []
    for h in columns:
        cell = unicode(row[h])
        if clip_col and len(cell) >= 19:
            cell = cell[:16] + '...'
        assembled.append(cell)
    return t_format.format(*tuple(assembled))


def diff_reporter(font_a, font_b, comp_data,
                  comp_order=comp_order,
                  markdown=False, output_lines=10, verbose=False):
    """Generate a cli report.
    comp_order: A user defined list denoting the order of comparison
                categories."""
    report = []
    h1 = '# ' if markdown else ''
    h2 = '## ' if markdown else ''

    title = '{}Diffenator\n'.format(h1)
    subtitle = '{}{} vs {}'.format(
        h2, os.path.basename(font_a), os.path.basename(font_b)
    )
    report.append(title)
    report.append(subtitle)

    comp_order = comp_order if comp_order else comp_data.keys()
    for category in comp_order:
        for sub_category in comp_data[category]:
            if comp_data[category][sub_category]:
                report.append(
                    '\n\n**%s %s %s**\n' % (
                        category,
                        len(comp_data[category][sub_category]),
                        sub_category
                    )
                )
                report.append(
                    dict_table(
                        comp_data[category][sub_category][:output_lines],
                        column_mapping[(category, sub_category)],
                        markdown=markdown)
                )
            elif verbose:
                report.append('\n\n**%s %s**\n' % (category, sub_category))
                report.append('No differences')
    return ''.join(report)


STYLE_TERMS = [
    'Hairline',
    'ExtraLight',
    'UltraLight',
    'Light',
    'Regular',
    'Book',
    'Medium',
    'SemiBold',
    'Bold',
    'ExtraBold',
    'Black',
    'Italic',
    'Oblique',
    'SemiCondensed',
    'Condensed',
    'Expanded',
    'SemiExpanded',
    'Narrow',
    'Compressed',
    'Semi',
    'Demi',
    'Extra',
    'Ultra',
    'Demi',
]


def stylename_from_name(name):
    """Extract the stylename from a string"""
    string = []
    for i in name.split():
        if i.lower() in [s.lower() for s in STYLE_TERMS]:
            string.append(i)
    stylename = ' '.join(string)
    return stylename


def _axis_loc_from_name(vf_font, style_name):
    """Get VF axis location from a style name"""
    vf_instance_idxs = [n.subfamilyNameID for n in vf_font['fvar'].instances]
    vf_instance_names = [vf_font['name'].getName(n, 3, 1, 1033).toUnicode()
                         for n in vf_instance_idxs]
    vf_instance_coords = {n: i.coordinates for n, i in
                          zip(vf_instance_names, vf_font['fvar'].instances)}
    if not vf_instance_coords:
        raise Exception('{} has no fvar instances'.format(vf_font.path))

    if style_name not in vf_instance_names:
        raise Exception(('Instance "{}"" not found in '
                         'fvar instances. Available [{}]'.format(
            style_name, ', '.join(vf_instance_names))
        ))
    return vf_instance_coords[style_name]


def vf_instance_from_static(vf_font, static_font):
    """Instantiate a VF using a static font's nametable.
    Returned instance is in-memory"""
    style_name = stylename_from_name(
            static_font['name'].getName(4, 3, 1, 1033).toUnicode()
    )
    print 'Getting instance {}'.format(style_name)
    return vf_instance(vf_font, style_name)


def vf_instance(font, instance_name):
    """Instantiate a VF using an instance name.
    Returned instance is in-memory."""
    loc = _axis_loc_from_name(font, instance_name)
    instance = instantiateVariableFont(font, loc, inplace=True)
    instance.is_variable = True
    return instance
