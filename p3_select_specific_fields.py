#!/usr/bin/env python3
import json
import os
import pprint
import re
import shutil
import subprocess
import webbrowser
from mako.template import Template
import p0_menus as p
import p1_select_contract as p1
import p2_select_templates as p2

p0_root_abs_dir = os.path.dirname(os.path.abspath(__file__))  # root directory where the program is located
p3_fields_rel_dir = ''  # currently working fields directory
p3_all_specific_fields_l = []  # list of fields that are product specific, read from p1e_specific_fields_d_of_d
p3_selected_fields_values_by_prod_d = {}  # field values for current product, as stored in mako_input.json
p3_body_svg = ''  # content of label_template_body.svg

p3_default_fields_l = ["xl_prod_spec", "u_parc", 'plstc_bg']
p3_f = None  # info on fields directory currently being edited
p3_d = {
    "selected_fields": list(p3_default_fields_l),
    "template_header": '',
    "header_height": 7,
    "page_view_box_w": 170,
    "page_view_box_h": 257,
}


# todo: if in memory check version, else is on disk load, else create default
# todo: check that when change contracts all fields with previous information is updated
# todo: make only one function to see one template, one product, or one contract

def load_p3_all_specific_fields_l():
    global p3_all_specific_fields_l

    if not p1.p1e_specific_fields_d_of_d:
        p1.load_p1e_specific_fields_d_of_d()
    p3_all_specific_fields_l = list(next(iter(p1.p1e_specific_fields_d_of_d.values())))


def save_template_info_json():
    global p3_f
    global p3_d

    p3_f = os.path.join(p1.p1_contract_abs_dir + '/' + p3_fields_rel_dir, 'template-info.json')
    with open(p3_f, 'w') as f:
        json.dump(p3_d, f, ensure_ascii = False)


def build_template_header_n_body(some_rel_dir = None):
    """
    copy header, also template if necessary, build body from template.svg copy that is in repository directory
    """

    from_abs_dir = os.path.join(p0_root_abs_dir + '/common', some_rel_dir if some_rel_dir else '1.Outer_box_外箱')
    to_abs_dir = os.path.join(p1.p1_contract_abs_dir, some_rel_dir if some_rel_dir else '1.Outer_box_外箱')

    # copy the label_template if necessary
    template_fr = os.path.join(to_abs_dir, 'label_template.svg')
    if not os.path.exists(template_fr):
        shutil.copy(os.path.join(from_abs_dir, 'label_template.svg'), to_abs_dir)
    body_fw = os.path.join(to_abs_dir, 'label_template_body.svg')

    global p3_body_svg
    with open(template_fr) as fr, open(body_fw, 'w') as fw:
        write_b = False
        lines = fr.readlines()
        for i in range(len(lines) - 1):
            if r'</metadata>' in lines[i]:
                write_b = True
                continue
            if write_b:
                p3_body_svg += lines[i]
                fw.write(lines[i])

    # and copy the label_template_header there
    if not os.path.exists(os.path.join(to_abs_dir, 'label_template_header.svg')):
        shutil.copy(os.path.join(p0_root_abs_dir + '/common', 'label_template_header.svg'), to_abs_dir)


def load_o_create_p3_fields_info_f():
    global p3_f
    global p3_d
    global p3_fields_rel_dir
    global p3_default_fields_l

    if p3_fields_rel_dir:
        # either read data,
        p3_f = os.path.join(p1.p1_contract_abs_dir + '/' + p3_fields_rel_dir, 'template-info.json')
        if os.path.exists(p3_f):
            with open(p3_f) as f:
                p3_d = json.load(f)
        # or populate missing fields with default information relative to the directory
        # other default information is set at variable initialization
        else:
            p3_d['template_header'] = p3_fields_rel_dir[p3_fields_rel_dir.rfind('_') + 1:]
        return True
    else:
        print('!\n! The contract directory does not contain subdirectories: cannot load or create labels\n!')
        return False


def make_mako_input_values_json(some_rel_dir):
    """
    Creates a json file with variables and values necessary to mako rendering
    :param some_rel_dir:
    :return:
    """
    # will be set in this function
    global p3_selected_fields_values_by_prod_d
    # make sure global variables are set in all situations, outside the loop to do it once only
    if not p1.p1b_indics_from_contract_l:
        p1.load_p1b_indics_from_contract_l()
    if not p1.p1_all_products_to_be_processed_set:
        p1.load_p1_all_products_to_be_processed_set()
    if load_o_create_p3_fields_info_f():
        # make a skeleton for p3_selected_fields_values_by_prod_d with key = prod
        idx = 0
        temp_d = {}
        for prod in p1.p1_all_products_to_be_processed_set:
            temp_d[prod] = {'i': idx + 1, 'prod_n': prod}
            idx += 1

        # populate the skeleton
        for indc_d in p1.p1b_indics_from_contract_l:  # loop over the big one once
            if indc_d['prod_nr'] in p1.p1_all_products_to_be_processed_set:
                if indc_d['what'] in p3_d['selected_fields']:  # loop over the smaller more
                    temp_d[indc_d['prod_nr']][indc_d['what']] = indc_d['info']

        # build p3_selected_fields_values_by_prod_d with key = i - 1
        for v in temp_d.values():
            p3_selected_fields_values_by_prod_d[v['i'] - 1] = v

        filename = os.path.join(p1.p1_contract_abs_dir + '/' + some_rel_dir, 'mako_input.json')
        with open(filename, 'w') as f:
            json.dump(p3_selected_fields_values_by_prod_d, f, ensure_ascii = False)
    else:
        print('!\n! No template has been selected for display\n!')


def render_1_template_1_product():
    # building the html page
    p3_fields_abs_dir = os.path.join(p1.p1_contract_abs_dir, p3_fields_rel_dir)
    filename = os.path.join(p3_fields_abs_dir, 'label_template_header.svg')
    with open(filename) as h:
        header = h.read()
    svg_out = os.path.join(p3_fields_abs_dir, 'page_0.svg')
    with open(svg_out, 'w') as f:
        f.write(header)
        filename = os.path.join(p3_fields_abs_dir, 'label_template_body.svg')
        mako_template = Template(filename = filename, input_encoding = 'utf-8')
        f.write(mako_template.render(**p3_selected_fields_values_by_prod_d[0]))
        f.write('</svg>')
    subprocess.Popen([r'firefox', svg_out])


def suggest_spacing_calc(lgth, template_view_box):
    n_of_templates_per_dim = int(lgth // template_view_box)
    return min(10, int((lgth - n_of_templates_per_dim * template_view_box) / max(1, (n_of_templates_per_dim - 1))))


def render_1_template_all_products():
    """
    Print min and max spacing depending on # of templates to be laid in rows & columns
    """
    global p3_fields_rel_dir
    global p3_selected_fields_values_by_prod_d
    global p3_fields_rel_dir

    from_abs_dir = os.path.join(p0_root_abs_dir + '/common', p3_fields_rel_dir)
    with open(os.path.join(from_abs_dir, 'label_template.svg')) as f:
        contents = f.read()
        m = re.search(r'(?<=viewBox=")(\d) (\d) (\d+.*\d*) (\d+\.*\d*)', contents)
        if m.groups()[0] != '0' or m.groups()[1] != '0':
            print("Error in building 'label_template.svg': origin is not (0, 0), exiting program ...")
            exit()

        template_view_box_w = float(m.groups()[2])
        template_view_box_h = float(m.groups()[3])  # template_view_box_h, template_view_box_h
    spacing_w = suggest_spacing_calc(p3_d['page_view_box_w'], template_view_box_w)  # first horizontally, w = width
    spacing_h = suggest_spacing_calc(p3_d['page_view_box_h'] - p3_d['header_height'],
                                     template_view_box_h)  # then vertically

    """
    assemble prepared svg files
    output to out.svg
    """
    p3_fields_abs_dir = os.path.join(p1.p1_contract_abs_dir, p3_fields_rel_dir)

    family = re.search(r'(?<=font-family:)([\w-]+)', p3_body_svg).groups()[0]
    size = re.search(r'(?<=font-size:)(\d+\.*\d*\w*)', p3_body_svg).groups()[0]
    style = re.search(r'(?<=font-style:)([\w-]+)', p3_body_svg).groups()[0]

    assert template_view_box_w + spacing_w <= p3_d['page_view_box_w'], \
        "write_templates: ! template + spacing width don't fit in the page"
    assert template_view_box_h + spacing_h <= p3_d['page_view_box_h'], \
        'write_templates: ! template + spacing height don\'t fit in the page'

    # printing templates in pages, when a page is full, open a new one
    svg_in = os.path.join(p3_fields_abs_dir, 'label_template_header.svg')
    with open(svg_in) as h:
        header = h.read()

    mako_template = Template(filename = os.path.join(p3_fields_abs_dir, 'label_template_body.svg'),
                             input_encoding = 'utf-8')

    N = len(p3_selected_fields_values_by_prod_d)  # nr of products in the contract
    page = 1  # nr of page being built
    i = 0  # index of the template to print
    ox = - spacing_w + horizontal_centering_offset(template_view_box_w, spacing_w)
    oy = - spacing_h + p3_d['header_height']

    while i < N:  # enumerating over each item in the contract
        # opening a new page
        svg_out = os.path.join(p3_fields_abs_dir, f'page_{page}.svg')
        with open(svg_out, 'w') as f:
            f.write(header)
            f.write("<g transform='translate(20, 20)'>\n")
            if page == 1:
                f.write(
                    "<g>\n<text transform='translate(0, 5)' "
                    f"style='font-family:{family};font-size:{size};font-style:{style}'>1. 外箱的唛头</text>\n</g>\n")
            while oy + template_view_box_h + spacing_h <= p3_d['page_view_box_h'] and i < N:
                while ox + template_view_box_w + spacing_w <= p3_d['page_view_box_w'] and i < N:
                    offset_x = ox + spacing_w
                    offset_y = oy + spacing_h
                    f.write(r"<g transform = 'translate(" + f"{offset_x}, {offset_y})'>\n")
                    f.write(mako_template.render(**p3_selected_fields_values_by_prod_d[i]))
                    f.write('</g>\n')
                    ox += template_view_box_w + spacing_w
                    i += 1
                ox = - spacing_w + horizontal_centering_offset(template_view_box_w, spacing_w)
                oy += template_view_box_h + spacing_h
            oy = - spacing_h + p3_d['header_height']
            f.write('\n</g>\n</svg>\n')
        webbrowser.get('firefox').open_new_tab(svg_out)
        page += 1


def render_all_templates_with_default_specific_fields():
    global p3_fields_rel_dir
    global p3_d
    global p3_all_specific_fields_l

    # read existing templates
    drs = p2.p2_load_templates_info_l()
    if drs:
        # for each template that has been created as a subdir to p1.p1_contract_abs_dir
        for p3_fields_rel_dir in drs:
            # use data on disk, if not on disk create with default values
            if load_o_create_p3_fields_info_f():
                # and save to disk
                save_template_info_json()
                build_template_header_n_body(p3_fields_rel_dir)
                make_mako_input_values_json(p3_fields_rel_dir)
                render_1_template_1_product()
                render_1_template_all_products()


def display_or_load_output_overview():
    global p3_fields_rel_dir
    global p3_d

    print('~~~ Overview')
    _, drs, _ = next(os.walk(p1.p1_contract_abs_dir))
    for dr in drs:
        print(dr)
        p3_fields_rel_dir = dr
        if load_o_create_p3_fields_info_f():
            print('\t', p3_d['selected_fields'])
    print('~~~')


def add_fields():
    global p3_f
    global p3_fields_rel_dir
    global p3_all_specific_fields_l

    if not p1.p1e_specific_fields_d_of_d:
        p1.load_p1e_specific_fields_d_of_d()
    p3_all_specific_fields_l = list(next(iter(p1.p1e_specific_fields_d_of_d.values())))
    # select from p3_all_specific_fields_l and put in p3_d['selected_fields']
    while True:
        print(f'~~~ Already selected:\n{p3_d["selected_fields"]}\n~~~ Can be added:')
        not_yet_l = []
        for o in p3_all_specific_fields_l:
            if o not in p3_d['selected_fields']:
                not_yet_l.append(o)
        for i in range(len(not_yet_l)):
            print(str(i) + ' ' + not_yet_l[i])
        print('~~~')
        s = input('Enter nr of indicator to add, \'b\' to return : ')
        if s == 'b':
            os.system('clear')
            break
        else:
            try:
                s_i = int(s)
                if s_i in range(len(not_yet_l)):
                    p3_d['selected_fields'].append(not_yet_l[s_i])
                    # break
                else:
                    print('!\n! Integer, but not an option, try again\n!')
            except ValueError:
                print('!\n! That\'s not an integer, try again\n!')
    save_template_info_json()


def del_fields():
    global p3_f

    while True:
        print(f'~~~ Already selected:')
        for i in range(len(p3_d['selected_fields'])):
            print(f'{i}. {p3_d["selected_fields"][i]}')
        print(f'~~~')
        s = input('Enter nr of indicator to delete, \'b\' to return : ')
        if s == 'b':
            os.system('clear')
            break
        else:
            try:
                s_i = int(s)
                if s_i in range(len(p3_d['selected_fields'])):
                    del p3_d['selected_fields'][s_i]
                    # break
                else:
                    print('!\n! Integer, but not an option, try again\n!')
            except ValueError:
                print('!\n! That\'s not an integer, try again\n!')

    save_template_info_json()


def display_specific_fields_for_all_products():
    # make sure global variables are set in all situations, outside the loop to do it once only
    if not p1.p1_all_products_to_be_processed_set:
        p1.load_p1_all_products_to_be_processed_set()
    if not p1.p1b_indics_from_contract_l:
        p1.load_p1b_indics_from_contract_l()

    if not p1.p1e_specific_fields_d_of_d:
        p1.load_p1e_specific_fields_d_of_d()
    p1e_l = list(next(iter(p1.p1e_specific_fields_d_of_d.values())))

    # building the header
    tmp_l = [8 * ' ']
    for f in p1e_l:
        tmp_l.append(f)
    dsp_l = [tmp_l]

    # building the body
    spec_by_prod = {}
    for prod in p1.p1_all_products_to_be_processed_set:
        spec_by_prod[prod] = {}
    for d in p1.p1b_indics_from_contract_l:
        if d['what'] in p1e_l:
            spec_by_prod[d['prod_nr']][d['what']] = d['info']

    for prod in spec_by_prod.keys():
        tmp_l = [prod]
        for k in spec_by_prod[prod].keys():
            tmp_l.append(spec_by_prod[prod][k])
        dsp_l.append(tmp_l)

    m = 0
    for l_l in dsp_l:
        for ls in l_l:
            m = max(m, len(str(ls)))
    s = ''
    for l_l in dsp_l:
        for ls in l_l:
            s += (m - len(str(ls))) * ' ' + str(ls)
        s += '\n'
    print(s)


def p3_select_specific_fields_context_func():
    display_specific_fields_for_all_products()
    print('~~~ Now processing contract #: ', p1.p1_contract_nr if p1.p1_contract_nr else None)
    print('~~~ Now working on template: ', p3_fields_rel_dir)
    print('~~~ Specific fields selected so far:', p3_d['selected_fields'])
    print('\n>>> Select an action: ')


def select_a_template_n_edit_fields():
    global p3_fields_rel_dir

    # read existing templates
    drs = p1.read_dirs(p1.p1_contract_abs_dir)
    if drs:
        print(f'~~~ Now processing contract #: {p1.p1_contract_nr}')
        print('>>> Select template to edit:\n')
        for i in range(len(drs)):
            print(str(i) + '. ' + drs[i][2:])
        while True:
            s = input('\nEnter nr of directory to delete_all_data_on_selected_contract, \'b\' to return : ')
            if s == 'b':
                os.system('clear')
                break
            else:
                try:
                    s_i = int(s)
                    if s_i in range(len(drs)):
                        os.system('clear')
                        p3_fields_rel_dir = drs[s_i]
                        # load fields already selected for template as they are on file
                        if load_o_create_p3_fields_info_f():
                            print(f'now ready to work on {p3_fields_rel_dir}')
                        while True:
                            p3_select_specific_fields_context_func()
                            s = input('\'a\' to add a field\n'
                                      '\'d\' to delete a field\n'
                                      '\'b\' to go back\n'
                                      '~~~\n')
                            if s == 'b':
                                os.system('clear')
                                break
                            elif s == 'a':
                                add_fields()
                            elif s == 'd':
                                del_fields()
                            else:
                                print(f'{s} is not an option, try again')
                        break
                    else:
                        print('!\n! Integer, but not an option, try again\n!')
                except ValueError:
                    print('!\n! That\'s not an integer, try again\n!')

        save_template_info_json()
        build_template_header_n_body(p3_fields_rel_dir)
        make_mako_input_values_json(p3_fields_rel_dir)
        render_1_template_1_product()
    else:
        return


def display_selected_fields():
    with open(os.path.join(p1.p1_contract_abs_dir, 'p4_' + p1.p1_contract_nr + '_fields_from_contract_l.json')) as f:
        p3_fields_from_contract_l = json.load(f)
    indic_val_d = {}
    for option in p3_all_specific_fields_l:
        temp_d = {}
        for indic in p3_fields_from_contract_l:
            if indic['what'] == option:
                temp_d[indic['prod_nr']] = indic['info']
        indic_val_d[option] = temp_d

    for option in p3_all_specific_fields_l:
        nr_tabs = 1 if len(option) >= 8 else 2
        print(option, nr_tabs * '\t', list(indic_val_d[option].values()))
    print('\nAlready selected: ', p3_d['selected_fields'], '\n')
    print('Currently processing ', p3_fields_rel_dir)


def display_p3_fields_info_d():
    global p3_d
    print('~~~ Reading template-info global value ~~~')
    pprint.pprint(p3_d)
    print(p3_d)
    print('~~~ Finished reading template-info global value ~~~')


def display_p3_fields_info_f():
    global p3_f
    global p3_d

    if p3_d:
        if os.path.exists(p3_f):
            print('~~~ Reading template-info.json file contents ~~~')
            with open(p3_f) as f:
                pprint.pprint(f.read())
            print('~~~ File template-info.json closed ~~~')
    else:
        print(f'\nFile {p3_f} not built yet\n')


def close_svg_for_output(fw, svg_out):
    fw.write('\n</g>\n</svg>\n')
    fw.close()
    webbrowser.get('firefox').open_new_tab(svg_out)


def open_svg_for_output(fw, header, page, svg_out):
    global p3_d
    assert fw == fw
    assert svg_out == svg_out

    svg_out = os.path.join(p1.p1_contract_abs_dir, f'page_{page}.svg')
    fw = open(svg_out, 'w')
    fw.write(header)
    fw.write("<g transform='translate(20, 20)'>\n")  # todo: reset with page margins
    return fw, svg_out


def horizontal_centering_offset(template_view_box_w, spacing_w):
    n_of_templates_per_row = int(p3_d['page_view_box_w'] // template_view_box_w)
    result = (p3_d['page_view_box_w'] - n_of_templates_per_row * template_view_box_w - (
        n_of_templates_per_row - 1) * spacing_w) / 2
    return result


def render_all_template_all_products():
    """

    """
    global p3_fields_rel_dir
    global p3_d
    global p3_all_specific_fields_l
    global p3_selected_fields_values_by_prod_d
    global p3_body_svg

    # load data from p1.p1e_specific_fields_d_of_d, put in a list of dicts
    load_p3_all_specific_fields_l()

    # read existing templates
    drs = p2.p2_load_templates_info_l()
    if drs:
        svg_out = ''
        oy = 0
        fw = None
        template_nr = 0
        page = 1  # nr of page being built
        for p3_fields_rel_dir in drs:
            template_nr += 1
            build_template_header_n_body(p3_fields_rel_dir)
            # loading data previously used with this template
            load_o_create_p3_fields_info_f()
            # opening a new page
            p3_fields_abs_dir = os.path.join(p1.p1_contract_abs_dir, p3_fields_rel_dir)
            # printing header template in page_# svg
            svg_in = os.path.join(p3_fields_abs_dir, 'label_template_header.svg')
            with open(svg_in) as h:
                header = h.read()
            # printing body template in page_# svg
            family = re.search(r'(?<=font-family:)([\w-]+)', p3_body_svg).groups()[0]
            size = re.search(r'(?<=font-size:)(\d+\.*\d*\w*)', p3_body_svg).groups()[0]
            style = re.search(r'(?<=font-style:)([\w-]+)', p3_body_svg).groups()[0]
            if page == 1:
                # open the first web page, it will be closed when there is no space left, and a new one opened
                fw, svg_out = open_svg_for_output(fw, header, page, svg_out)
            # from template build the body necessary to multiply templates  todo: make sure all fields are in place
            make_mako_input_values_json(p3_fields_rel_dir)
            # read view box values from template_body so as to compute spacings
            to_abs_dir = os.path.join(p1.p1_contract_abs_dir, p3_fields_rel_dir)
            with open(os.path.join(to_abs_dir, 'label_template.svg')) as f:
                contents = f.read()
                m = re.search(r'(?<=viewBox=")(\d) (\d) (\d+.*\d*) (\d+\.*\d*)', contents)
                if m.groups()[0] != '0' or m.groups()[1] != '0':
                    print("Error in building 'label_template.svg': origin is not (0, 0), exiting program ...")
                    exit()

                template_view_box_w = float(m.groups()[2])
                template_view_box_h = float(m.groups()[3])  # template_view_box_h, template_view_box_h
            spacing_w = suggest_spacing_calc(p3_d['page_view_box_w'], template_view_box_w)  # horizontally, w = width
            spacing_h = suggest_spacing_calc(p3_d['page_view_box_h'] - p3_d['header_height'],
                                             template_view_box_h)  # then vertically
            ox = - spacing_w + horizontal_centering_offset(template_view_box_w, spacing_w)
            if page == 1:
                oy = - spacing_h
            assert template_view_box_w + spacing_w <= p3_d['page_view_box_w'], \
                "write_templates: ! template width + spacing width don't fit in the page"
            assert template_view_box_h + spacing_h <= p3_d['page_view_box_h'], \
                'write_templates: ! template height + spacing height don\'t fit in the page'
            # write the header for this directory
            oy += p3_d['header_height']  # todo: check if at end of page
            fw.write(
                f"<g>\n<text transform='translate(0, {oy})' "
                f"style='font-family:{family};font-size:{size};font-style:{style}'>\
                {template_nr}. {p3_d['template_header']}</text>\n</g>\n"
            )
            # run mako.template.Template
            mako_template = Template(
                filename = os.path.join(p3_fields_abs_dir, 'label_template_body.svg'),
                input_encoding = 'utf-8'
            )
            N = len(p3_selected_fields_values_by_prod_d)  # nr of products in the contract
            i = 0  # index of the template to print

            while i < N:  # writing vertically while there are templates to print
                # writing horizontally while there templates to print
                while ox + template_view_box_w + spacing_w <= p3_d['page_view_box_w'] and i < N:
                    offset_x = ox + spacing_w
                    offset_y = oy + spacing_h
                    fw.write(r"<g transform = 'translate(" + f"{offset_x}, {offset_y})'>\n")
                    fw.write(mako_template.render(**p3_selected_fields_values_by_prod_d[i]))
                    fw.write('</g>\n')
                    ox += template_view_box_w + spacing_w
                    i += 1
                ox = - spacing_w + horizontal_centering_offset(template_view_box_w, spacing_w)
                oy += template_view_box_h + spacing_h
                # with the new oy, check if there is still space to write the next one, if not open a new page
                if oy + template_view_box_h + spacing_h > p3_d['page_view_box_h']:
                    close_svg_for_output(fw, svg_out)
                    page += 1
                    fw, svg_out = open_svg_for_output(fw, header, page, svg_out)
                    oy = - spacing_h + p3_d['header_height']
            # after last item is written, write the next header if needed
        close_svg_for_output(fw, svg_out)

    else:
        print('No template directory found, go back to general menu and create one or more templates')


context_func_d = {
    'select_specific_fields': p3_select_specific_fields_context_func,
}


def init():
    # make sure p1 infrastructure is in place
    if not p1.p1_load_contract_info_d():
        print('p1 has not run successfully')
    if not p1.read_dirs(p1.p1_contract_abs_dir):
        p2.create_default_templates()

    # initializing menus last, so that context functions display most recent information
    p.menu = 'select_specific_fields'
    if not p.main_menu:
        p.main_menu = p.menu
    p.menus = {
        p.menu: {
            '0': render_all_template_all_products,
            '1': render_all_templates_with_default_specific_fields,
            '2': display_or_load_output_overview,
            '3': select_a_template_n_edit_fields,
            '4': display_selected_fields,
            '6': p1.display_p1_contract_info_d,
            '7': p1.display_p1_contract_info_f,
            '8': display_p3_fields_info_d,
            '9': display_p3_fields_info_f,
            'b': p.back_to_main,
            'q': p.normal_exit,
        }
    }
    if not p.main_menus:
        p.main_menus = p.menus
    if __name__ == '__main__':
        p.mod_lev_1_menu = p.menu
        p.mod_lev_1_menus = p.menus
    p.context_func_d = {**p.context_func_d, **context_func_d}


def main():
    """ Driver """
    init()
    p.run()


if __name__ == '__main__':
    main()
