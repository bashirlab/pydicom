#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reformat the UID list (Table A-1 PS3.6-2015b) from the PS3.6 docbook file to
Python syntax

Write the dict element as:
    UID: (name, type, info, is_retired)

    * info is extra information extracted from very long names, e.g.
        which bit size a particular transfer syntax is default for
    * is_retired is 'Retired' if true, else ''

The results are sorted in ascending order of the Tag.


Based on Rickard Holmberg's docbook_to_uiddict2013.py.
"""

import os
import xml.etree.ElementTree as ET

try:
    import urllib2
    # python2
except ImportError:
    import urllib.request as urllib2
    # python3

PYDICOM_DICT_FILENAME = '../../pydicom/_uid_dict.py'
DICT_NAME = 'UID_dictionary'


def write_dict(fp, dict_name, attributes):
    """Write the `dict_name` dict to file `fp`.

    Parameters
    ----------
    fp : file
        The file to write the dict to.
    dict_name : str
        The name of the dict variable.
    attributes : list of str
        List of attributes of the dict entries.
    """
    uid_entry = "('{UID Name}', '{UID Type}', '{UID Info}', '{Retired}')"
    entry_format = "'{UID Value}': %s" % (uid_entry)

    fp.write("\n%s = {\n    " % dict_name)
    fp.write(",  # noqa\n    ".join(entry_format.format(**attr)
                                    for attr in attributes))
    fp.write("  # noqa\n}\n")


def parse_docbook_table(book_root, caption):
    """Parses the XML `book_root` for the table with `caption`.

    Parameters
    ----------
    book_root
        The XML book root
    caption : str
        The caption of the table to parse

    Returns
    -------
    row_attrs : list of dict
        A list of the Element dicts generated by parsing the table.
    """
    br = '{http://docbook.org/ns/docbook}'  # Shorthand variable

    # Find the table in book_root with caption
    for table in book_root.iter('%stable' % (br)):
        if table.find('%scaption' % (br)).text == caption:

            def parse_row(column_names, row):
                """Parses `row` for the DICOM Element data.

                The row should be <tbody><tr>...</tr></tbody>
                Which leaves the following:
                    <td><para>Value 1</para></td>
                    <td><para>Value 2</para></td>
                    etc...
                Some rows are
                    <td><para><emphasis>Value 1</emphasis></para></td>
                    <td><para><emphasis>Value 2</emphasis></para></td>
                    etc...
                There are also some without text values
                    <td><para/></td>
                    <td><para><emphasis/></para></td>

                Parameters
                ----------
                column_names : list of str
                    The column header names
                row
                    The XML for the header row of the table

                Returns
                -------
                dict
                    {header1 : val1, header2 : val2, ...} representing the
                    information for the row.
                """
                cell_values = []
                for cell in row.iter('%spara' % (br)):
                    # If we have an emphasis tag under the para tag
                    emph_value = cell.find('%semphasis' % (br))
                    if emph_value is not None:

                        # If there is a text value add it, otherwise add ""
                        if emph_value.text is not None:
                            # 200b is a zero width space
                            cell_values.append(emph_value.text.strip()
                                               .replace("\u200b", ""))
                        else:
                            cell_values.append("")

                    # Otherwise just grab the para tag text
                    else:
                        if cell.text is not None:
                            cell_values.append(cell.text.strip()
                                               .replace("\u200b", ""))
                        else:
                            cell_values.append("")

                cell_values[3] = ''
                cell_values.append('')

                if '(Retired)' in cell_values[1]:
                    cell_values[4] = 'Retired'
                    cell_values[1] = cell_values[1].replace('(Retired)',
                                                            '').strip()

                if ':' in cell_values[1]:
                    cell_values[3] = cell_values[1].split(':')[-1].strip()
                    cell_values[1] = cell_values[1].split(':')[0].strip()

                return {key: value for key,
                        value in zip(column_names, cell_values)}

            # Get all the Element data from the table
            column_names = ['UID Value',
                            'UID Name',
                            'UID Type',
                            'UID Info',
                            'Retired']

            row_attrs = [parse_row(column_names, row)
                         for row in table.find('%stbody' % (br))
                         .iter('%str' % (br))]

            return row_attrs


attrs = []

url_base = "http://medical.nema.org/medical/dicom/current/source/docbook"
url = '%s/part06/part06.xml' % (url_base)
response = urllib2.urlopen(url)
tree = ET.parse(response)
root = tree.getroot()

attrs += parse_docbook_table(root, "UID Values")

for attr in attrs:
    attr['UID Name'] = attr['UID Name'].replace('&', 'and')
    attr['UID Value'] = attr['UID Value'].replace('\u00ad', '')

py_file = open(PYDICOM_DICT_FILENAME, "w")
py_file.write('"""DICOM UID dictionary auto-generated by %s"""\n'
              % (os.path.basename(__file__)))

write_dict(py_file, DICT_NAME, attrs)

py_file.close()

print("Finished, wrote %d UIDs" % len(attrs))
