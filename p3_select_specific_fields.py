#!/usr/bin/env python3
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import warnings
import webbrowser
from tkinter.filedialog import askopenfilename
import render_barcode as rb

from lxml import etree
from mako.template import Template

import m_menus as m
import p1_select_contract as p1
import p2_select_templates as p2

p3_all_specific_fields_l = []  # list of fields from p1e_specific_fields_d_of_d
p3_body_svg = ""  # contents of label_template_body.svg
# p3_default_fields_l = ['xl_prod_spec', 'u_parc']
p3_d = {}
p3_f = ""
p1.p1_d["fields_rel_dir"] = ""  # currently working fields directory
p3_selected_fields_values_by_prod_d = {}  # field values as in .mako_input.json
page_view_box_w = 0
page_view_box_h = 0
env_d = {}
browser_path = ""
pdf_reader_path = ""


# Utility functions ####################################################################################################
def load_o_create_required_apps_path():
    global env_d
    global browser_path
    global pdf_reader_path
    # either read existing data
    env_f = os.path.join(m.root_abs_dir, "environment.json")
    if os.path.exists(env_f):
        with open(env_f, encoding="utf8") as f:
            env_d = json.load(f)

    # or populate missing fields with default information
    if os.name == "posix":
        if "firefox_path" not in env_d:
            env_d["firefox_path"] = r"/usr/bin/firefox"
        if "chrome_path" not in env_d:
            env_d["chrome_path"] = r"/usr/bin/google-chrome"
        if "inkscape_path" not in env_d:
            env_d["inkscape_path"] = r"/usr/bin/inkscape"
        if "qpdf_path" not in env_d:
            env_d["qpdf_path"] = r"/usr/bin/qpdf"
        if "FoxitReader_path" not in env_d:
            env_d["FoxitReader_path"] = r"/usr/bin/FoxitReader"
        if "xreader_path" not in env_d:
            env_d["xreader_path"] = r"/usr/bin/xreader"
    elif os.name == "nt":
        if "firefox_path" not in env_d:
            env_d[
                "firefox_path"
            ] = r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
        webbrowser.register(
            "firefox", None, webbrowser.BackgroundBrowser(env_d["firefox_path"])
        )  # in Windows, when not in path
        if "chrome_path" not in env_d:
            env_d[
                "chrome_path"
            ] = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        webbrowser.register(
            "chrome", None, webbrowser.BackgroundBrowser(env_d["chrome_path"])
        )  # in Windows, when not in path
        if "inkscape_path" not in env_d:
            env_d["inkscape_path"] = r"C:\Program Files\Inkscape\bin\inkscape.exe"
        if "qpdf_path" not in env_d:
            env_d["qpdf_path"] = r"C:\Program Files no reg\qpdf-10.0.1\bin\qpdf.exe"
        if "FoxitReader_path" not in env_d:
            env_d[
                "FoxitReader_path"
            ] = r"C:\Program Files (x86)\Foxit Software\Foxit Reader\FoxitReader.exe"
        if "acroreader_path" not in env_d:
            env_d[
                "acroreader_path"
            ] = r"C:\Program Files\Adobe\Reader 11.0\Reader\acrord32.exe"
    else:
        m.error = True
        print("|\n| Unsupported OS\n|")
        sys.exit()

    # associating browser_path to browser chosen in 'environment.json'
    if "browser" not in env_d:
        env_d["browser"] = "firefox"
    if env_d["browser"] in env_d["firefox_path"]:
        browser_path = env_d["firefox_path"]
    elif env_d["browser"] in env_d["chrome_path"]:
        browser_path = env_d["chrome_path"]
    else:
        m.error = True
        print(
            "|\n| Could not associate 'browser_path' with 'browser': check 'environment.json'"
        )

    # associating pdf_reader_path to pdf_reader chosen in 'environment.json'
    if "pdf_reader" not in env_d:
        env_d["pdf_reader"] = "FoxitReader"
    if env_d["pdf_reader"] in env_d["FoxitReader_path"]:
        pdf_reader_path = env_d["FoxitReader_path"]
    elif os.name == "posix" and env_d["pdf_reader"] in env_d["xreader_path"]:
        pdf_reader_path = env_d["xreader_path"]
    elif os.name == "nt" and env_d["pdf_reader"] in env_d["acroreader_path"]:
        pdf_reader_path = env_d["acroreader_path"]
    else:
        m.error = True
        print(
            "|\n| Could not associate 'pdf_reader_path' with 'pdf_reader': check 'environment.json'"
        )
    with open(env_f, "w", encoding="utf8") as fw:
        json.dump(env_d, fw, ensure_ascii=False, indent=4)


def test_linux_environment():
    global env_d
    global browser_path
    global pdf_reader_path
    print("Browser:", 111 * "#")
    subprocess.run([env_d["browser"], "--version"], executable=browser_path)
    print("Inkscape:", 110 * "#")
    subprocess.run(["inkscape", "--version"], executable=env_d["inkscape_path"])
    print("qpdf:", 114 * "#")
    subprocess.run(["qpdf", "--version"], executable=env_d["qpdf_path"])
    print("pdf_reader:", 108 * "#")
    warnings.simplefilter("ignore", ResourceWarning)
    subprocess.Popen(
        [env_d["pdf_reader"]],
        executable=pdf_reader_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    warnings.simplefilter("default", ResourceWarning)
    print(120 * "#")


def my_webbrowser_open_new_tab(browser, tab):
    global browser_path
    warnings.simplefilter("ignore", ResourceWarning)
    webbrowser.get(browser).open_new_tab(tab)
    warnings.simplefilter("default", ResourceWarning)


def test_browser_no_wait():
    global env_d
    my_webbrowser_open_new_tab(env_d["browser"], "www.inkscape.org")


def test_inkscape_and_wait():
    global env_d
    subprocess.run(["inkscape"], executable=env_d["inkscape_path"])


def test_qpdf_and_wait():
    global env_d
    print("qpdf:", 114 * "#")
    subprocess.run(["qpdf", "--version"], executable=env_d["qpdf_path"])
    print(120 * "#")


def test_pdf_reader_no_wait():
    global env_d
    global pdf_reader_path
    warnings.simplefilter("ignore", ResourceWarning)
    subprocess.run(
        [env_d["pdf_reader"]],
        executable=pdf_reader_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    warnings.simplefilter("default", ResourceWarning)


def p3_d_load_o_create():
    global p3_f
    global p3_d
    # global p3_default_fields_l
    global page_view_box_w
    global page_view_box_h

    p1.doc_set_up_load_o_create()
    page_view_box_w = 210 - 2 * p1.doc_setup_d["margin_w"]  # Assuming A4
    page_view_box_h = 297 - 2 * p1.doc_setup_d["margin_h"]  # Assuming A4

    if p1.p1_d["fields_rel_dir"]:
        # either read data,
        p3_f = os.path.join(
            os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]),
            "template-info.json",
        )
        if os.path.exists(
            p3_f
        ):  # file exists, check that all default value are present, if not print a msg
            with open(p3_f, encoding="utf8") as f:
                p3_d = json.load(
                    f
                )  # loads selected_fields, template_header, header_height, barcodes

        # or populate missing fields with default information relative to the directory
        if "pictures" not in p3_d.keys():
            p3_d["pictures"] = False
        else:
            if p3_d["pictures"] is True:
                if not p1.all_products_to_be_processed_set:
                    p1.p1_all_products_to_be_processed_set_load()
                p3_d["pictures"] = {}
                for prod_nr in list(p1.all_products_to_be_processed_set):
                    p3_d["pictures"][prod_nr] = [
                        {"x": 0, "y": 0, "coef": 1.0, "file": "pic_0.png"}
                    ]

        if "barcodes" not in p3_d.keys():
            p3_d["barcodes"] = False
        else:
            if p3_d["barcodes"] is True:
                p3_d["barcodes"] = [{"coef": 1.0, "x": 0, "y": 0}]

        if "pre_processing" not in p3_d.keys():
            p3_d["pre_processing"] = False
        else:
            if p3_d["pre_processing"] is True:
                p3_d["pre_processing"] = {
                    "new_field": {"field": "", "regex": "", "repl": "", "default": ""}
                }

        if "partially_populated_fields" not in p3_d:
            p3_d["partially_populated_fields"] = False
        else:
            if p3_d["partially_populated_fields"] is True:
                p3_d["partially_populated_fields"] = [
                    "my_partially_populated_field_name"
                ]

        if "selected_fields" not in p3_d:
            # p3_d['selected_fields'] = ['xl_prod_spec', 'u_parc']
            p3_d["selected_fields"] = []

        if "header_height" not in p3_d.keys():
            p3_d["header_height"] = 7

        if "template_header" not in p3_d.keys():
            p3_d["template_header"] = (
                p1.p1_d["fields_rel_dir"][p1.p1_d["fields_rel_dir"].rfind("_") + 1 :]
                + "唛头"
            )

        save_template_info_json()
        return True
    else:
        m.error = True
        print(
            "|\n| The contract directory does not contain subdirectories: cannot load or create labels\n|"
        )
        return False


def save_template_info_json():
    global p3_f
    global p3_d

    p3_f = os.path.join(
        os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]),
        "template-info.json",
    )
    with open(p3_f, "w", encoding="utf8") as f:
        json.dump(p3_d, f, ensure_ascii=False, indent=4)


def reset_globals():
    global p3_all_specific_fields_l
    global p3_body_svg
    # global p3_default_fields_l
    global p3_d
    global p3_f
    global p3_selected_fields_values_by_prod_d
    global page_view_box_h
    global page_view_box_w

    p3_all_specific_fields_l = []
    p3_body_svg = ""
    # p3_default_fields_l = ['xl_prod_spec', 'u_parc']
    # p3_d = {
    #     "selected_fields": list(p3_default_fields_l),
    #     "template_header": '',
    #     "header_height": 7,
    # }
    p3_d = {}
    p3_f = ""
    p1.p1_d["fields_rel_dir"] = ""
    p3_selected_fields_values_by_prod_d = {}
    page_view_box_h = 0
    page_view_box_w = 0


def p3_all_specific_fields_l_load():
    global p3_all_specific_fields_l

    if not p1.p1e_specific_fields_d_of_d:
        p1.p1e_specific_fields_d_of_d_n_p3_needed_vars_load()
    p3_all_specific_fields_l = list(next(iter(p1.p1e_specific_fields_d_of_d.values())))


# produce barcodes #####################################################################################################
def prod_n_to_barcode(prod_nr):  # sourcery skip
    temp_s = ""
    for char in prod_nr:
        if char.isnumeric():
            temp_s += char
    while len(temp_s) < 12:
        temp_s = "3" + temp_s if (12 - len(temp_s)) % 2 == 1 else "0" + temp_s
    return temp_s


def create_barcode_file(prod_n):
    brcd_tmplt = os.path.join(
        os.path.join(m.root_abs_dir, "common"), "barcode_template.svg"
    )

    # put a directory for barcodes
    brcd_dir = os.path.join(
        os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]), "bcode"
    )
    if not os.path.exists(brcd_dir):
        os.mkdir(brcd_dir)
    brcd_f = os.path.join(brcd_dir, prod_n + ".svg")
    rb.Barcode().run(
        args=[
            "-t=Ean13",
            f"-d={prod_n_to_barcode(prod_n)} ",
            f"-l=20 ",
            f"--output={brcd_f}",
            f"{brcd_tmplt} ",
        ]
    )
    return brcd_f


# Edit template and field structures ###################################################################################
def fields_from_template():
    template_s = os.path.join(
        os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]),
        "label_template.svg",
    )
    if not os.path.exists(template_s):
        m.error = True
        print(
            f"|\n| Cannot access '{os.path.join(p1.p1_d['fields_rel_dir'], 'label_template.svg')}': no such file\n|"
        )
    with open(template_s, encoding="utf8") as fr:
        lines = fr.readlines()
    template_fields_set = set()
    for line in lines:
        finds = re.findall(r"(\${)(.+?)(})", line)
        for find in finds:
            template_fields_set.add(find[1])
    return template_fields_set


def check_all_templates_have_correct_fields():
    _, drs, _ = next(os.walk(p1.p1_cntrct_abs_dir))
    for p1.p1_d["fields_rel_dir"] in drs:
        dump_fields_rel_dir()
        p3_d_load_o_create()
        check_if_selected_template_requirements_are_met()


def scrap_template_for_fields():  # todo: probably needs to be re-eng with check_if_template_requirements_are_met
    template_fields = fields_from_template()
    for x in ["t", "i", "prod_n"]:
        if x in template_fields:
            template_fields.remove(x)
    for f in template_fields:
        if f not in p3_d["selected_fields"]:
            p3_d["selected_fields"].append(f)
    print(f'Template scrapped, selected_fields: {p3_d["selected_fields"]}')
    save_template_info_json()


def add_fields():
    global p3_f
    global p3_all_specific_fields_l

    if not p1.p1e_specific_fields_d_of_d:
        p1.p1e_specific_fields_d_of_d_n_p3_needed_vars_load()
    p3_all_specific_fields_l = list(next(iter(p1.p1e_specific_fields_d_of_d.values())))
    # select from p3_all_specific_fields_l and put in p3_d['selected_fields']
    while True:
        print(
            f'\n~~~ Already selected:\n{p3_d["selected_fields"]}\n\n~~~ Can be added:'
        )
        not_yet_l = []
        for o in p3_all_specific_fields_l:
            if o not in p3_d["selected_fields"]:
                not_yet_l.append(o)
        for i in range(len(not_yet_l)):
            print(str(i) + " " + not_yet_l[i])
        print("\n~~~")
        s = input("Enter nr of indicator to add, 'b' to return : ")
        if s == "b":
            m.clear()
            break
        else:
            try:
                s_i = int(s)
                if s_i in range(len(not_yet_l)):
                    p3_d["selected_fields"].append(not_yet_l[s_i])
                    # break
                else:
                    print("|\n| Integer, but not an option, try again\n|")
            except ValueError:
                print("|\n| That's not an integer, try again\n|")
    save_template_info_json()


def del_fields():
    global p3_f

    while True:
        print(f"\n~~~ Already selected:")
        for i in range(len(p3_d["selected_fields"])):
            print(f'{i}. {p3_d["selected_fields"][i]}')
        print(f"\n~~~")
        s = input("Enter nr of indicator to delete, 'b' to return : ")
        if s == "b":
            m.clear()
            break
        else:
            try:
                s_i = int(s)
                if s_i in range(len(p3_d["selected_fields"])):
                    del p3_d["selected_fields"][s_i]
                    # break
                else:
                    print("|\n| Integer, but not an option, try again\n|")
            except ValueError:
                print("|\n| That's not an integer, try again\n|")

    save_template_info_json()


def display_specific_fields_for_all_products():
    # make sure global variables are set in all situations, outside the loop to do it once only
    if not p1.all_products_to_be_processed_set:
        p1.p1_all_products_to_be_processed_set_load()
    if not p1.p1b_indics_from_contract_l:
        p1.p1b_indics_from_contract_l_load()

    if not p1.p1e_specific_fields_d_of_d:
        p1.p1e_specific_fields_d_of_d_n_p3_needed_vars_load()
    p1e_l = list(next(iter(p1.p1e_specific_fields_d_of_d.values())))

    # building the header
    tmp_l = [8 * " "]
    for f in p1e_l:
        tmp_l.append(f)
    dsp_l = [tmp_l]

    spec_by_prod = p1.p1e_specific_fields_d_of_d

    # filling missing information with ***
    # adding 'prod_nr' to the list and sorting
    for prod in spec_by_prod.keys():
        tmp_l = [prod]
        for value in p1e_l:
            if value not in spec_by_prod[prod].keys():
                spec_by_prod[prod][value] = "***"
            tmp_l.append(spec_by_prod[prod][value])
        dsp_l.append(tmp_l)

    length = 0
    for l_l in dsp_l:
        for ls in l_l:
            length = max(length, len(str(ls)))
    s = ""
    for l_l in dsp_l:
        for ls in l_l:
            s += (length - len(str(ls))) * " " + str(ls)
        s += "\n"
    print(s)


def edit_fields():
    while True:
        print(
            "\n~~~ Now working on template: ",
            p1.p1_d["fields_rel_dir"] if p1.p1_d["fields_rel_dir"] else "None",
        )
        s = input(
            "'a' to add a field\n"
            "'d' to delete a field\n"
            "'b' to go back_后退\n"
            "~~~\n"
        )
        if s == "b":
            m.clear()
            break
        elif s == "a":
            add_fields()
        elif s == "d":
            del_fields()
        else:
            print(f"{s} is not an option, try again")

    save_template_info_json()
    mako_input_json_load_o_create(force_recreate=True)


def edit_a_template_menu():
    print("\n~~~ select a template to edit ~~~")
    m.mod_lev_1_menu = m.menu
    m.menu = "edit_a_template"
    select_a_template()


def select_a_template():
    drs = p2.p2_load_templates_info_l()
    if drs:
        for i in range(len(drs)):
            print(str(i) + ". " + drs[i][2:])
        while True:
            s = input("\nEnter nr of template to be edited, 'b' to return : ")
            if s == "b":
                m.clear()
                m.menu = m.mod_lev_1_menu
                break
            else:
                try:
                    s_i = int(s)
                    if s_i in range(len(drs)):
                        m.clear()
                        p1.p1_d["fields_rel_dir"] = drs[s_i]
                        dump_fields_rel_dir()
                        # load fields already selected for template as they are on file
                        p3_d_load_o_create()
                        break
                    else:
                        print("|\n| Integer, but not an option, try again\n|")
                except ValueError:
                    print("|\n| That's not an integer, try again\n|")


def edit_label_template_svg():
    global env_d
    body_file = os.path.join(
        os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]),
        ".label_template_body.svg",
    )
    if os.path.exists(body_file):
        os.remove(
            os.path.join(
                os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]),
                ".label_template_body.svg",
            )
        )
    label_template_file = os.path.join(
        os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]),
        "label_template.svg",
    )
    if os.path.exists(label_template_file):
        subprocess.run(
            ["inkscape", label_template_file], executable=env_d["inkscape_path"]
        )


def edit_paragraph_headers():
    # list existing directories, each containing a template
    drs = p2.p2_load_templates_info_l()
    if drs:
        # giving a default directory if none has been set before
        if not p1.p1_d["fields_rel_dir"]:
            p1.p1_d["fields_rel_dir"] = drs[0]
        print(f'\n~~~ Now processing contract #: {p1.p1_d["cntrct_nr"]}')
        print(">>> Select template to edit:\n")
        for i in range(len(drs)):
            print(str(i) + ". " + drs[i][2:])
        while True:
            s = input("\nEnter nr of template to be edited, 'b' to return : ")
            if s == "b":
                m.clear()
                break
            else:
                try:
                    s_i = int(s)
                    if s_i in range(len(drs)):
                        m.clear()
                        p1.p1_d["fields_rel_dir"] = drs[s_i]
                        dump_fields_rel_dir()
                        # load fields already selected for template as they are on file
                        if p3_d_load_o_create():
                            print(f"now ready to work on {p1.p1_d['fields_rel_dir']}")
                        while True:
                            # select_specific_fields_context_func()
                            s = input(
                                "'m' to use a multi-lines header\n"
                                "'d' to use a single line default header\n"
                                "'b' to go back_后退\n"
                                "~~~\n"
                            )
                            if s == "b":
                                m.clear()
                                break
                            elif s == "m":
                                # multi-lines header
                                p3_d["template_header"] = (
                                    "<tspan x='5' y='10'>Lorem ipsum dolor sit amet, "
                                    "consectetur adipiscing elit, sed do eiusmod "
                                    "tempor</tspan><tspan x='5' y='15'>incididunt ut labore et "
                                    "dolore magna aliqua. Ut enim minim veniam, quis nostrud "
                                    "exercitation ullamco laboris nisi</tspan> <tspan x='5' "
                                    "y='20'>ut aliquip ex commodo consequat. Duis aute irure "
                                    "dolor in reprehenderit in voluptate velit esse cillum "
                                    "dolore eu</tspan> "
                                )
                                p3_d["header_height"] = 20
                            elif s == "d":
                                # single line header
                                p3_d["template_header"] = (
                                    p1.p1_d["fields_rel_dir"][
                                        p1.p1_d["fields_rel_dir"].rfind("_") + 1 :
                                    ]
                                    + "唛头"
                                )
                                p3_d["header_height"] = 7
                            else:
                                print(f"{s} is not an option, try again")
                        break
                    else:
                        print("|\n| Integer, but not an option, try again\n|")
                except ValueError:
                    print("|\n| That's not an integer, try again\n|")

        save_template_info_json()
        mako_input_json_load_o_create()
        produce_svg_w_watermarks_1_template_1_product_n_cover_page()
    else:
        return


# process svg_w_watermarks and its utility functions ###################################################################
def dump_fields_rel_dir():
    """ Leaves a trace of the last edited template by saving p1.p1_d in the root directory file 'program-info.json'. """
    global p3_d

    prog_info_json_f = os.path.join(m.root_abs_dir, "program-info.json")
    with open(prog_info_json_f, "w", encoding="utf8") as fw:
        json.dump(p1.p1_d, fw, ensure_ascii=False, indent=4)


def check_if_selected_template_requirements_are_met():
    m.hide_context = True
    template_fields_set = fields_from_template()
    for x in ["t", "i", "prod_n"]:
        if x in template_fields_set:
            template_fields_set.remove(x)
    for x in template_fields_set.copy():
        if x[-3:] == "_fr":
            template_fields_set.remove(x)

    if p3_d["pre_processing"]:
        for x in p3_d["pre_processing"]:
            template_fields_set.remove(x)

    # print(f'Template in {p1.p1_d['fields_rel_dir']} uses {template_fields_set}')
    # print(f'Fields selected to feed data are  {p3_d["selected_fields"]}')
    diff_set = template_fields_set - set(p3_d["selected_fields"])
    if diff_set:
        missing_in_selected_fields_l = [
            f for f in template_fields_set if f not in p3_d["selected_fields"]
        ]
        print(
            "The template requires the following fields but those\n"  # todo: manage the 'better_spec' case
            "were not found in 'template-info.json'/'selected_fields' list: ",
            missing_in_selected_fields_l,
        )
    else:
        print("'label_template.svg' and 'template-info.json' fields requirements match")


def mako_input_json_load_o_create(force_recreate=False):
    """
    Creates a json file with variables and values necessary to mako rendering
    :return:
    """
    global p3_selected_fields_values_by_prod_d

    check_if_selected_template_requirements_are_met()  # todo: inspect this function
    # make sure global variables are initialized in all situations, outside the loop to do it once only
    fields_abs_dir = os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"])
    mako_input_json_s = os.path.join(fields_abs_dir, ".mako_input.json")
    if pathlib.Path(mako_input_json_s).exists() and not force_recreate:
        with open(mako_input_json_s, encoding="utf8") as fr:
            p3_selected_fields_values_by_prod_d = json.load(fr)
    else:
        if not p1.p1b_indics_from_contract_l:
            p1.p1b_indics_from_contract_l_load()
        if not p1.all_products_to_be_processed_set:
            p1.p1_all_products_to_be_processed_set_load()

        # make a skeleton for p3_selected_fields_values_by_prod_d with key = prod
        temp_d = {}
        idx = 0
        for prod in sorted(p1.all_products_to_be_processed_set):
            temp_d[prod] = {"i": str(idx + 1), "prod_n": prod}
            if (
                "partially_populated_fields" in p3_d
                and p3_d["partially_populated_fields"]
            ):
                for field in p3_d["partially_populated_fields"]:
                    temp_d[prod][field] = ""
                    if field[-3:] == "_zh":
                        temp_d[prod][field[:-2] + "fr"] = ""
            idx += 1

        # prepare to insert translations if needed
        with open(
            os.path.join(os.path.join(m.root_abs_dir, "common"), "zh_fr.json"),
            encoding="utf8",
        ) as f:
            zh_fr_d = json.load(f)

        # prepare to create files of 'pre_processing' data if needed
        pre_proc_data_d = {}
        if "pre_processing" in p3_d.keys() and p3_d["pre_processing"]:
            pre_proc_data_d = {
                p3_d["pre_processing"][key]["field"]: set()
                for key in p3_d["pre_processing"].keys()
            }

        # populate the skeleton
        for indc_d in p1.p1b_indics_from_contract_l:  # loop over the big one once
            if (
                indc_d["prod_nr"] in p1.all_products_to_be_processed_set
            ):  # todo: possibly set products to be processed
                what_zh = indc_d["what"]
                if what_zh in p3_d["selected_fields"]:  # loop over the smaller more
                    temp_d[indc_d["prod_nr"]][what_zh] = indc_d["info"]
                    # internal convention: all indics with name finishing with _zh will be translated into French
                    # with ./common/zh_fr.json
                    if what_zh[-3:] == "_zh":
                        info_zh = indc_d["info"]
                        if info_zh in zh_fr_d:
                            what_fr = what_zh[:-2] + "fr"
                            temp_d[indc_d["prod_nr"]][what_fr] = zh_fr_d[info_zh]
                        else:
                            m.error = True
                            print(f"|\n| {info_zh} not in zh_fr.json\n|\n")

                    # add fields data for fields that will be later re-processed
                    if pre_proc_data_d and what_zh in pre_proc_data_d:
                        pre_proc_data_d[what_zh].add(indc_d["info"])

        # write data text files for fields that will be re-processed
        if pre_proc_data_d:
            for k, v in pre_proc_data_d.items():
                with open(os.path.join(fields_abs_dir, "." + k + ".txt"), "w") as fw:
                    fw.write(v.__str__())

        # build the dictionary p3_selected_fields_values_by_prod_d with key = i - 1
        for v in temp_d.values():
            p3_selected_fields_values_by_prod_d[str(int(v["i"]) - 1)] = v

        # adding new fields being derived from existing ones, as defined in template-info.json
        if "pre_processing" in p3_d and p3_d["pre_processing"]:  # case True or dic()
            for new_field in p3_d["pre_processing"].keys():
                new_field_d = p3_d["pre_processing"][new_field]
                if not (new_field_d["field"] and new_field_d["regex"]):
                    print("|\n| Data missing in template-info.json / pre_processing\n|")
                    exit()
                for k in p3_selected_fields_values_by_prod_d.keys():
                    string = p3_selected_fields_values_by_prod_d[k][
                        new_field_d["field"]
                    ]
                    regex = new_field_d["regex"]
                    default = new_field_d["default"]
                    repl = new_field_d["repl"]
                    out_field = re.sub(regex, repl, string)
                    p3_selected_fields_values_by_prod_d[k][new_field] = (
                        out_field if out_field else default
                    )

        with open(mako_input_json_s, "w", encoding="utf8") as f:
            json.dump(
                p3_selected_fields_values_by_prod_d, f, ensure_ascii=False, indent=4
            )


def pre_process():
    mako_input_json_load_o_create(force_recreate=True)
    filename = os.path.join(
        os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]),
        ".mako_input.json",
    )
    subprocess.call(["jq", ".", filename])
    # subprocess.call(['/usr/bin/xed', filename])
    # with open(filename, encoding='utf8') as f:
    #     pprint.pprint(f.read())


def util_print_tags_in_svg_files():
    m.hide_context = True
    fields_abs_dir = os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"])
    filename = askopenfilename(initialdir=fields_abs_dir)
    if filename:
        tree = etree.parse(filename)
        root = tree.getroot()
        tags = set()
        for element in root.iter():
            tag = element.tag.split("}")[1]
            tags.add(tag)
            print(tag)
        print(f"tags: {tags}")
    else:
        m.error = True
        print("|\n| No file selected\n|")


def produce_svg_w_watermarks_all_templates_all_products(
    only_1_temp=False, only_1_prod=False
):
    """"""
    global p3_d
    global p3_all_specific_fields_l
    global p3_selected_fields_values_by_prod_d
    global p3_body_svg
    global page_view_box_h
    global page_view_box_w

    fields_abs_dir = os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"])

    def suggest_spacing_calc(lgth, template_view_box):
        # if # of ranks exceeds length to print or unadjusted
        n_of_templates_per_dim = int(lgth // template_view_box)  # // integer division
        return min(
            20,
            int(
                (lgth - n_of_templates_per_dim * template_view_box)
                / max(1, (n_of_templates_per_dim - 1))
            ),
        )
        # else or adjusted

    def horizontal_centering_offset():
        global page_view_box_w

        n_of_templates_per_row = int(page_view_box_w // template_view_box_w)
        return (
            page_view_box_w
            - n_of_templates_per_row * template_view_box_w
            - (n_of_templates_per_row - 1) * spacing_w
        ) / 2

    def create_template_body():
        """
        copy header, also template if necessary, build body from template.svg copy that is in repository directory
        """
        global p3_body_svg

        from_abs_dir = os.path.join(
            os.path.join(m.root_abs_dir, "common"), p1.p1_d["fields_rel_dir"]
        )

        # copy the label_template intro the repertory if necessary
        svg_readable_file_in = os.path.join(fields_abs_dir, "label_template.svg")
        svg_insertable_file_out = os.path.join(
            fields_abs_dir, ".label_template_body.svg"
        )
        if not pathlib.Path(svg_readable_file_in).exists():
            shutil.copy(
                os.path.join(from_abs_dir, "label_template.svg"), fields_abs_dir
            )

        # create label_template_body.svg
        strip_readable_svg_file_for_insert(
            svg_readable_file_in, svg_insertable_file_out
        )
        with open(svg_insertable_file_out) as fr:
            p3_body_svg = fr.read()

    def strip_readable_svg_file_for_insert(
        svg_readable_file_in, svg_insertable_file_out
    ):
        m.hide_context = True
        tree = etree.parse(svg_readable_file_in)
        root = tree.getroot()
        for element in root.iter():
            if element.tag.split("}")[1] == "svg":
                for attribute in element.attrib:
                    element.attrib.pop(attribute)
            if element.tag.split("}")[1] in ["guide", "namedview", "metadata"]:
                element.getparent().remove(element)
        tree.write(svg_insertable_file_out)

    def open_svg_for_output():
        global p3_d
        global page_view_box_h
        global env_d

        # fields_abs_dir = os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d['fields_rel_dir'])
        if only_1_temp:
            if only_1_prod:
                svg_out3 = os.path.join(fields_abs_dir, ".1_product.svg")
            else:
                svg_out3 = os.path.join(fields_abs_dir, f".1_template_{page}.svg")
        else:
            svg_out3 = os.path.join(p1.p1_cntrct_abs_dir, f"page_{page}.svg")
        fw1 = open(svg_out3, "w", encoding="utf8")
        fw1.write(header)
        fw1.write(
            f'<rect x="0" y="0"\n'
            f'width="210" height="297"\n'
            f'style="fill:none;stroke-width:0.5;stroke-opacity:1;stroke:#ff00ff" />\n'
        )
        fw1.write(
            f'<rect x="{p1.doc_setup_d["margin_w"]}" y="{p1.doc_setup_d["margin_h"]}"\n'
            f'width="{210 - 2 * p1.doc_setup_d["margin_w"]}" height="{297 - 2 * p1.doc_setup_d["margin_h"]}"\n'
            f'style="fill:none;stroke-width:0.5;stroke-opacity:1;stroke:#ff00ff" />\n'
        )
        page_x = 100  # page middle - 5mm to center text, assuming A4
        page_y = int(page_view_box_h + 3 * (297 - page_view_box_h) / 4)
        fw1.write(
            f"<g>\n<text transform='translate({page_x}, {page_y})' "
            f"style='font-family:{family};font-size:{size};font-style:{style}'>-- {page} --</text>\n</g>\n"
        )
        # assuming A4
        fw1.write(
            f"<g transform='translate({p1.doc_setup_d['margin_w']}, {p1.doc_setup_d['margin_h']} )'>\n"
        )
        return fw1, svg_out3

    def close_svg_for_output(fw2, svg_out2):
        fw2.write("</g>\n</svg>\n")
        fw2.close()
        my_webbrowser_open_new_tab(env_d["browser"], svg_out2)

    # def extract_svg_for_inserting(inkscape_filename, insert_filename):
    #     with open(inkscape_filename, encoding = 'utf8') as fr, open(insert_filename, 'w', encoding = 'utf8') as fwe:
    #         write_b = False
    #         lines = fr.readlines()
    #         for idx in range(len(lines) - 1):
    #             if r'</metadata>' in lines[idx]:
    #                 write_b = True
    #                 continue
    #             if write_b:
    #                 fwe.write(lines[idx])

    # get information good for all products
    lngth = len(p1.all_products_to_be_processed_set)  # nr of products in the contract
    if lngth == 0:
        print("init lngth failed")
        exit()

    # load p1.p1e_specific_fields_d_of_d, put in a list of dicts
    p3_all_specific_fields_l_load()

    # read existing templates
    drs = [p1.p1_d["fields_rel_dir"]] if only_1_temp else p2.p2_load_templates_info_l()
    oy = 0
    if drs:
        svg_out = ""  # svg output filename
        fw = None  # and its file handler
        template_nr = 0  # number templates so as to make headers
        page = 1  # nr of page being built

        # looping on template directories
        for p1.p1_d["fields_rel_dir"] in drs:
            fields_abs_dir = os.path.join(
                p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]
            )

            # check that, if pictures need to be inserted, a directory for picture files does exist
            p3_d_load_o_create()

            create_template_body()
            with open(
                os.path.join(
                    os.path.join(m.root_abs_dir, "common"), ".label_template_header.svg"
                ),
                encoding="utf8",
            ) as h:
                header = h.read()
            template_nr += 1
            # loading data previously used with this template
            # p3_d_load_o_create()

            # opening a new page, printing header template in 'page_#.svg'
            # printing body template in page_# svg
            try:
                family = re.search(
                    r"(?<=font-family:)'([\w| ]+)'", p3_body_svg
                ).groups()[0]
            except AttributeError:
                family = "sans-serif"
            # family = re.search(r"(?<=font-family:)'([\w| |-]+)'", p3_body_svg).groups()[0]  produces a warning
            try:
                size = re.search(
                    r"(?<=font-size:)(\d+\.*\d*\w*)", p3_body_svg
                ).groups()[0]
            except AttributeError:
                size = "3.6px"
            try:
                style = re.search(r"(?<=font-style:)([\w-]+)", p3_body_svg).groups()[0]
            except AttributeError:
                style = "normal"

            # open the first web page, it will be closed when there is no space left, then a new one will be opened
            if page == 1:
                fw, svg_out = open_svg_for_output()

            # from the editable template, build the 'label_template.svg' that will be used to multiply templates
            mako_input_json_load_o_create(force_recreate=True)

            # read view box values from template_body so as to compute spacings
            with open(
                os.path.join(fields_abs_dir, "label_template.svg"), encoding="utf8"
            ) as f:
                mako_template = Template(
                    filename=os.path.join(fields_abs_dir, ".label_template_body.svg"),
                    input_encoding="utf-8",
                )
                contents = f.read()
                measures = re.search(
                    r'(?<=viewBox=")(\d) (\d) (\d+.*\d*) (\d+\.*\d*)', contents
                )
                if measures.groups()[0] != "0" or measures.groups()[1] != "0":
                    print(
                        "Error in building 'label_template.svg': origin is not (0, 0), exiting program ..."
                    )
                    exit()
                template_view_box_w = float(measures.groups()[2])
                template_view_box_h = float(measures.groups()[3])

            # compute spacings
            spacing_w = suggest_spacing_calc(page_view_box_w, template_view_box_w)

            nr_rows = lngth // (page_view_box_w // template_view_box_w)
            vert_length_needed = nr_rows * template_view_box_h
            vert_length_avail = (
                page_view_box_h
                - p3_d["header_height"]
                - p1.doc_setup_d["page_1_vert_offset"]
            )
            spacing_h = (
                suggest_spacing_calc(
                    page_view_box_h - p3_d["header_height"], template_view_box_h
                )
                if vert_length_needed > vert_length_avail
                else 15
            )

            # write the header for this template
            if page == 1:
                oy = p1.doc_setup_d["page_1_vert_offset"] - spacing_h

            fw.write(
                f"<g>"
                f'<svg width="{page_view_box_w}" height="{p3_d["header_height"]}" '
                f'x="0" y="{oy + spacing_h}">\n'
                f'<rect x="0" y="0"\n'
                f'width="100%" height="100%"\n'
                f'style="fill:none;stroke-width:0.5;stroke-opacity:1;stroke:#ff00ff" />\n'
                f'<text x="0%" y="100%" dominant-baseline="text-after-edge" '
                f'style="font-family:{family};font-size:{size};font-style:{style}">'
                f'{template_nr}. {p3_d["template_header"]}</text>\n</svg>\n'
                f"</g>\n"
            )

            # run mako.template.Template
            ox = -spacing_w + horizontal_centering_offset()
            oy += p3_d["header_height"]
            i = 0  # index of the product to print

            # looping on products
            while i < (1 if only_1_prod else lngth):

                # writing horizontally while there templates to print
                while ox + template_view_box_w <= page_view_box_w and i < (
                    1 if only_1_prod else lngth
                ):
                    fw.write(
                        r"<g transform = 'translate("
                        + f"{ox + spacing_w}, {oy + spacing_h})'>\n"
                    )

                    # link a picture file if there is one to link
                    if type(p3_d["pictures"]) != "bool" and p3_d["pictures"]:
                        prod_nr = p3_selected_fields_values_by_prod_d[str(i)]["prod_n"]
                        if prod_nr in p3_d["pictures"].keys():
                            prod_nr_l = p3_d["pictures"][prod_nr]
                            for j in range(len(prod_nr_l)):
                                filename_rel = os.path.join(
                                    "pics", prod_nr_l[j]["file"]
                                )
                                filename_abs = os.path.join(
                                    fields_abs_dir, filename_rel
                                )

                                if pathlib.Path(filename_abs).exists():
                                    _, ext = os.path.splitext(filename_abs)
                                    dim_ = str(float(prod_nr_l[j]["coef"]) * 100) + "%"
                                    if ext == ".svg":
                                        i_filename = os.path.join(
                                            fields_abs_dir, "." + prod_nr_l[j]["file"]
                                        )
                                        if not pathlib.Path(i_filename).exists():
                                            strip_readable_svg_file_for_insert(
                                                filename_abs, i_filename
                                            )
                                        with open(i_filename, encoding="utf8") as f:
                                            fw.write(
                                                f"<g transform = 'matrix("
                                                f"{prod_nr_l[j]['coef']},0,0,"
                                                f"{prod_nr_l[j]['coef']}, "
                                                f"{prod_nr_l[j]['x']},{prod_nr_l[j]['y']}"
                                                ")'>\n"
                                                "<svg>\n"
                                            )

                                            fw.write(f.read())
                                            fw.write("</svg>\n" "</g>\n")
                                        os.remove(i_filename)
                                    else:
                                        fw.write(
                                            "<g>\n<svg>\n"
                                            f"<image xlink:href='{f'{filename_rel}'}' \n"
                                            f"x='{prod_nr_l[j]['x']}' y='{prod_nr_l[j]['y']}' \n"
                                            f"width='{dim_}' height='{dim_}' \n"
                                            "preserveAspectRatio='xMidyMid' \n"
                                            "style='image-rendering:optimizeQuality' />\n"
                                            "</svg>\n</g>\n"
                                        )
                                else:
                                    m.error = True
                                    print(
                                        f"|\n| Cannot access {filename_abs}: No such file \n"
                                        "| Make sure it exists as indicated by template-info.json\n|"
                                    )
                                    exit()

                    # create the path to the barcode file, would it exists
                    barcode_f = os.path.join(
                        os.path.join(
                            os.path.join(
                                p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"]
                            ),
                            "bcode",
                        ),
                        p3_selected_fields_values_by_prod_d[str(i)]["prod_n"] + ".svg",
                    )

                    if "barcodes" in p3_d and p3_d["barcodes"]:
                        brcd_l = list(p3_d["barcodes"])
                    else:
                        brcd_l = []

                    if brcd_l:
                        for k in range(len(brcd_l)):
                            if pathlib.Path(
                                create_barcode_file(
                                    p3_selected_fields_values_by_prod_d[str(i)][
                                        "prod_n"
                                    ]
                                )
                            ).exists():
                                with open(barcode_f, encoding="utf8") as f:
                                    fw.write(
                                        f"<g transform = 'matrix("
                                        f"{brcd_l[k]['coef']},0,0,{brcd_l[k]['coef']},"
                                        f"{brcd_l[k]['x']},{brcd_l[k]['y']}"
                                        ")'>\n<svg>\n"
                                    )
                                    fw.write(f.read())
                                    fw.write("\n</svg>\n</g>\n")

                    # print(  # for debug purposes
                    #     f'{p1.p1_d["fields_rel_dir"]} page: {page} ',
                    #     f'ox: {ox:3.1f}, oy: {oy:3.1f}',
                    #     f"idx: {p3_selected_fields_values_by_prod_d[str(i)]['i']}",
                    #     f"prod_nr: {p3_selected_fields_values_by_prod_d[str(i)]['prod_n']}"
                    # )
                    # print(  # for debug purposes
                    #     p1.p1_d['cntrct_nr'], template_nr, i, end = ', '
                    # )
                    # tmp_l = [k for k in list(p3_selected_fields_values_by_prod_d[str(i)].keys())[:8]]
                    # for k in tmp_l:
                    #     print(  # for debug purposes
                    #         ', ', k, p3_selected_fields_values_by_prod_d[str(i)][k], end = ''
                    #     )
                    # print()

                    fw.write(
                        mako_template.render(
                            contract_n=p1.p1_d["cntrct_nr"],
                            t=template_nr,
                            **p3_selected_fields_values_by_prod_d[str(i)],
                        )
                    )
                    fw.write("\n</g>\n")
                    ox += template_view_box_w + spacing_w
                    i += 1
                ox = -spacing_w + horizontal_centering_offset()
                oy += template_view_box_h + spacing_h
                # print(  # for debug purposes
                #     f'ox: {ox:3.1f} ox: {oy:3.1f}  test: {oy + template_view_box_h + spacing_h} > {page_view_box_h}'
                # )
                # check if there is still space to write the next one, if not open a new page
                if oy + template_view_box_h + spacing_h > page_view_box_h:
                    # to avoid printing a blank page when no data left
                    if i < (1 if only_1_prod else lngth) or template_nr != len(drs):
                        close_svg_for_output(fw, svg_out)
                        page += 1
                        fw, svg_out = open_svg_for_output()
                        if i == lngth:  # if at end of a list, then oy = 0
                            oy = 0
                        else:
                            oy = -spacing_h

            # after last item is written, write the next header if needed
        close_svg_for_output(
            fw, svg_out
        )  # close the last file without opening a new one
    else:
        print(
            "No template directory found, go back to general menu and create one or more templates"
        )


# Aggregate functions ##################################################################################################
def produce_svg_w_watermarks_1_template_1_product_n_cover_page():
    global p3_d
    global p3_selected_fields_values_by_prod_d
    global env_d

    # if no template has been selected, select the first one in the list
    cvr_pg_dir = p2.p2_load_templates_info_l()[0]
    if not p1.p1_d["fields_rel_dir"]:
        p1.p1_d["fields_rel_dir"] = cvr_pg_dir
        dump_fields_rel_dir()

    # generate a svg with mako rendering on the first product
    produce_svg_w_watermarks_all_templates_all_products(
        only_1_temp=True, only_1_prod=True
    )

    # if the cover page has been set and if this is the first template in the list then also create a cover page
    if p1.doc_setup_d["cover_page"] and p1.p1_d["fields_rel_dir"] == cvr_pg_dir:
        p3_d_load_o_create()
        p3_all_specific_fields_l_load()

        # print(  # for debug purposes
        #     f"From '..._doc_setup.json': cover_page = {p1.doc_setup_d['cover_page']}"
        # )
        # if p1.doc_setup_d['cover_page']:
        #     print("The label used for the cover page is from the layer 'label' in label_template.svg")

        # copy first label on cover page template
        fields_abs_dir = os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["fields_rel_dir"])
        svg_in = os.path.join(fields_abs_dir, ".1_product.svg")
        if svg_in:
            with open(svg_in, encoding="utf8") as fr:
                lines = fr.readlines()
            balance = 0
            keep_l = []
            tmp_l = []
            i = 0
            good_n = 0
            for line in lines:
                res1 = re.match(r"\s*<g", line)
                if res1:
                    balance += 1
                res2 = re.match(r"\s*</g>", line)
                if balance >= 3:
                    tmp_l.append(line)
                if res2:
                    if balance == 3:
                        keep_l.append(tmp_l)
                        i += 1
                        tmp_l = []
                    balance -= 1
                if 'label="label"' in line:
                    good_n = i
            with open(
                os.path.join(
                    os.path.join(m.root_abs_dir, "common"), ".cover_page_template.svg"
                ),
                encoding="utf8",
            ) as fr:
                lines = fr.readlines()
            svg_out = os.path.join(p1.p1_cntrct_abs_dir, ".cover_page_template.svg")
            with open(svg_out, "w", encoding="utf8") as fw:
                for i in range(len(lines) - 1):
                    fw.writelines(lines[i])
                fw.write('<g transform="matrix(1,0,0,1,15,45)">\n')
                for good in keep_l[good_n]:
                    fw.write(good)
                # fw.writelines(keep_l[good_n])
                fw.write("\n</g>\n")
                fw.write('<g transform="matrix(.25,0,0,.25,22,167)">\n')
                for good in keep_l[good_n]:
                    fw.write(good)
                # fw.writelines(keep_l[good_n])
                fw.write("\n</g>\n")
                fw.writelines(lines[len(lines) - 1])

            # run mako.template.Template
            mako_template = Template(filename=svg_out, input_encoding="utf-8")

            if not p3_selected_fields_values_by_prod_d:
                mako_input_json_load_o_create()

            # creating a file for the cover page and possibly linked images
            cover_s = os.path.join(p1.p1_cntrct_abs_dir, "page_0.svg")
            pics_fields_path = os.path.join(fields_abs_dir, "pics")
            pics_cntrct_path = os.path.join(p1.p1_cntrct_abs_dir, "pics")
            if os.path.exists(pics_fields_path):
                shutil.copytree(pics_fields_path, pics_cntrct_path, dirs_exist_ok=True)

            with open(cover_s, "w", encoding="utf8") as fw:
                fw.write(
                    mako_template.render(
                        contract_n=p1.p1_d["cntrct_nr"],
                        **p3_selected_fields_values_by_prod_d["0"],
                    )
                )
            my_webbrowser_open_new_tab(env_d["browser"], cover_s)
        else:
            print(
                f"{svg_in}: no such file, it should be built before attempting to build a cover page"
            )


def produce_svg_w_watermarks_1_template_all_products():
    if not p1.p1_d["fields_rel_dir"]:
        drs = p2.p2_load_templates_info_l()
        p1.p1_d["fields_rel_dir"] = drs[0]
    produce_svg_w_watermarks_all_templates_all_products(only_1_temp=True)


def produce_all_svg_n_print():
    produce_svg_w_watermarks_1_template_1_product_n_cover_page()
    produce_svg_w_watermarks_all_templates_all_products()
    remove_watermarks_n_produce_pdf_deliverable()


def produce_all_previous_production_options_n_print():
    load_o_create_required_apps_path()
    # read existing templates
    drs_l = p2.p2_load_templates_info_l()
    if drs_l:
        # for each template that has been created as a subdir to p1.p1_cntrct_abs_dir
        for p1.p1_d["fields_rel_dir"] in drs_l:
            dump_fields_rel_dir()
            # use data on disk, if not on disk create with default values
            if p3_d_load_o_create():
                print("Rendering 1 template, 1 product & cover page")
                produce_svg_w_watermarks_1_template_1_product_n_cover_page()
                print("Rendering 1 template, all products")
                produce_svg_w_watermarks_1_template_all_products()
    print("Rendering all templates, all products, and print")
    produce_all_svg_n_print()


# final process: unite list of 1-page pdf into final deliverable #######################################################
def remove_watermarks_n_produce_pdf_deliverable():
    """
    Remove all output files that may exist in root directory.

    Produce new ones: list filename.svg with watermark.

    remove watermarks, save in .filename.svg.

    use inkscape to export .filename.svg to .filename.pdf.

    unite all .filename.pdf into deliverable.pdf.

    display deliverable.pdf.
    """
    global env_d
    global pdf_reader_path
    # Remove all output files that may exist in root directory
    _, _, files = next(os.walk(p1.p1_cntrct_abs_dir))
    pdfs = [
        file
        for file in files
        if file.endswith(".pdf") or (file.endswith(".svg") and file[0] == ".")
    ]
    for file in pdfs:
        os.remove(os.path.join(p1.p1_cntrct_abs_dir, file))

    # Produce new ones: list filename.svg with watermark
    _, _, files = next(os.walk(p1.p1_cntrct_abs_dir))
    watermarked_svgs = sorted([f for f in files if f.endswith(".svg")])

    # remove watermarks, save in .filename.svg
    dot_pdfs = []
    for file in watermarked_svgs:
        # remove watermarks to make a printable .filename.svg
        printable_svg = os.path.join(p1.p1_cntrct_abs_dir, "." + file)
        bare_filename, _ = os.path.splitext(file)
        file = os.path.join(p1.p1_cntrct_abs_dir, file)
        with open(file, encoding="utf8") as fr, open(
            printable_svg, "w", encoding="utf8"
        ) as fw:
            for line in fr:
                fw.write(line.replace("fuchsia", "none").replace("#ff00ff", "none"))

        # use inkscape to export .filename.svg to .filename.pdf
        dot_pdf = os.path.join(p1.p1_cntrct_abs_dir, "." + bare_filename + ".pdf")
        p = subprocess.Popen(
            [  # here use Popen instead of run to manage inkscape hanging on Chinese Windows 7
                env_d["inkscape_path"],
                f"--export-filename={dot_pdf}",
                printable_svg,
            ],
            executable=env_d["inkscape_path"],
        )
        try:
            outs, errs = p.communicate(
                timeout=10
            )  # if inkscape has not exited in 10 sec, kill it
        except subprocess.TimeoutExpired:
            print(f"Process {p.pid} timed out before finishing")
            p.kill()
        else:
            # print('subprocess.Popen return code', p.returncode)
            if p.returncode is not None and p.returncode != 0:
                raise RuntimeError(
                    f"Failed command-line: {errs.decode(sys.stderr.encoding)}"
                )
        dot_pdfs.append(f"{dot_pdf}")

    # unite all .filename.pdf into deliverable.pdf
    deliverable_pdf = os.path.join(p1.p1_cntrct_abs_dir, p1.p1_d["cntrct_nr"] + ".pdf")
    subprocess.run(
        ["qpdf", "--empty", "--pages", *dot_pdfs, "--", deliverable_pdf],
        executable=env_d["qpdf_path"],
    )

    # display deliverable.pdf
    warnings.simplefilter("ignore", ResourceWarning)
    subprocess.Popen(
        [env_d["pdf_reader"], deliverable_pdf],
        executable=pdf_reader_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    warnings.simplefilter("default", ResourceWarning)


# Shell interface data & functions #####################################################################################
# noinspection PyPep8Naming,NonAsciiCharacters
def step_3__select_fields_to_print_for_each_template_选择每种标签类型的资料():
    def select_specific_fields_context_func(prompt=True):
        if not m.error and not m.hide_context:
            print("~~~ Step 3: Selecting fields to print for each template ~~~\n")
            display_specific_fields_for_all_products()
            print(
                "~~~ Now processing contract #: ",
                p1.p1_d["cntrct_nr"] if p1.p1_d["cntrct_nr"] else None,
            )
            print(
                "~~~ Now working on template: ",
                p1.p1_d["fields_rel_dir"]
                if p1.p1_d["fields_rel_dir"]
                else "None selected",
            )
            print("~~~ Specific fields selected so far:", p3_d["selected_fields"])
            print(60 * "-", "\n\n")
            if prompt:
                print("\n>>> Select an action: ")
        else:
            m.error = False
            m.hide_context = False

    context_func_d = {
        "select_specific_fields": select_specific_fields_context_func,
        "edit_a_template": select_specific_fields_context_func,
        "debug": select_specific_fields_context_func,
    }

    # make sure p1 infrastructure is in place
    if not p1.contract_info_d_load():
        print("p1 has not run successfully")
    if not p2.p2_load_templates_info_l():
        p2.load_or_create_templates()
    # read existing p3 infrastructure
    if "fields_rel_dir" not in p1.p1_d or not p1.p1_d["fields_rel_dir"]:
        p1.p1_d["fields_rel_dir"] = p2.p2_load_templates_info_l()[0]
        dump_fields_rel_dir()
    if not p3_d:
        p3_d_load_o_create()
    # read path to apps
    load_o_create_required_apps_path()

    # initializing menus last, so that context functions display most recent information
    m.menu = "select_specific_fields"
    if not m.main_menu:
        m.main_menu = m.menu
    # todo: menus should reflect acting on recognised situations
    # todo: change template, add / remove field
    # todo: check if template requirements are met
    m.menus = {
        m.menu: {
            "0": select_a_template,
            "1": produce_svg_w_watermarks_1_template_1_product_n_cover_page,
            "2": produce_svg_w_watermarks_1_template_all_products,
            "3": produce_svg_w_watermarks_all_templates_all_products,
            "4": produce_all_svg_n_print,
            "5": produce_all_previous_production_options_n_print,
            "55": remove_watermarks_n_produce_pdf_deliverable,
            "e": edit_a_template_menu,
            "11": pre_process,
            "12": check_if_selected_template_requirements_are_met,
            "13": check_all_templates_have_correct_fields,
            "b": m.back_to_main_退到主程序,
            "q": m.normal_exit_正常出口,
            "d": m.debug,
        },
        "edit_a_template": {
            "44": edit_label_template_svg,
            "0": scrap_template_for_fields,
            "1": check_if_selected_template_requirements_are_met,
            "2": edit_fields,
            "3": p1.process_selected_contract,
            "4": edit_paragraph_headers,
            "b": m.back_后退,
            "q": m.normal_exit_正常出口,
        },
        "debug": {
            "br": test_browser_no_wait,
            "in": test_inkscape_and_wait,
            "qp": test_qpdf_and_wait,
            "pr": test_pdf_reader_no_wait,
            "t": test_linux_environment,
            "tags": util_print_tags_in_svg_files,
            "b": m.back_后退,
            "q": m.normal_exit_正常出口,
        },
    }
    if not m.main_menus:
        m.main_menus = m.menus
    if __name__ == "__main__":
        m.mod_lev_1_menu = m.menu
        m.mod_lev_1_menus = m.menus
    m.context_func_d = {**m.context_func_d, **context_func_d}


def main():
    """ Driver """
    step_3__select_fields_to_print_for_each_template_选择每种标签类型的资料()
    m.run()


if __name__ == "__main__":
    main()
