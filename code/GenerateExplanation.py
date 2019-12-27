from lisptree3 import *
import re
import csv
import locale
import unicodedata
import xcolors
from bidict import bidict

from SpecHandler import SpecHandler

number_regex = re.compile("^-?(?:0|[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})*)(?:\.(?:\d+)?)?$")

color_codes = bidict({
    "R": "red",
    "O": "orange",
    "Y": "yellow",
    "G": "green",
    "C": "cyan",
    "b": "blue",
    "P": "purple",
    "M": "magenta",
    "p": "pink",
    "B": "black",
    "g": "gray",
    "W": "white"
})
color_values = color_codes.values()

def convert_value(raw_text):
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    if number_regex.match(raw_text) == None:
        return raw_text
    try: 
        return locale.atoi(raw_text)
    except ValueError: 
        try: 
            return locale.atof(raw_text)
        except ValueError:
            return raw_text

def remove_accents(raw_str):
    return str(unicodedata.normalize("NFKD", raw_str).encode('ASCII', 'ignore'), "utf-8")

def clean_grammatical_junk(raw_str):
    raw_str = re.sub(r"\s+$", "", raw_str)
    raw_str = re.sub(r"of$", "", raw_str)
    raw_str = re.sub(r"and$", "", raw_str)
    raw_str = re.sub(r"\s+$", "", raw_str)
    raw_str = re.sub(r"\s+", " ", raw_str)
    return raw_str

reference_regex = re.compile("\(\/(?P<gid>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(.+?)\/(?P=gid)\/\)")

def remove_references(reference_text):
    reference_text = reference_text.replace("[[DATA]]", "data")
    reference_text = reference_text.replace("[[INDEX]]", "index")
    reference_text = reference_text.replace("[[NEXT]]", "next")
    if reference_text == "meta[x-axis]":
        reference_text = "<<RETRIEVE>>what the x-axis represents by looking at the label on the x-axis"
    elif reference_text == "meta[y-axis]":
        reference_text = "<<RETRIEVE>>what the y-axis represents by looking at the label on the y-axis"
    elif reference_text[:11] == "meta[color:":
        color_name = reference_text[11:-10]
        reference_text = "<<RETRIEVE>>what " + color_name + " represents by looking at the legend"
    return re.sub(reference_regex, "'\g<2>'", reference_text)

def add_header_text(explanation):
    explanation = re.sub(r"<<RETRIEVE>>", "I looked up ", explanation)
    explanation = re.sub(r"<<COUNT>>", "I counted the ", explanation)
    explanation = re.sub(r"<<COMPUTE>>", "I computed the ", explanation)
    explanation = explanation + "."
    return explanation

class TextTemplate:
    def __init__(self, text):
        def generate_text(subtexts, keytext = "[!!]", indexing = 1):
            result_text = text
            for subtext_idx, subtext in enumerate(subtexts):
                target_token = "[!" + str(subtext_idx + indexing) + "]"
                result_text = result_text.replace(target_token, subtext)
            result_text = result_text.replace("[!!]", keytext)
            return result_text
        self.text_generator = generate_text
        
text_templates = {
    "argmax": TextTemplate("[!3] with the greatest [!4]"),
    "argmin": TextTemplate("[!3] with the smallest [!4]"),
    ">=": TextTemplate("greater than or equal to [!1]"),
    ">": TextTemplate("greater than [!1]"),
    "<=": TextTemplate("less than or equal to [!1]"),
    "<": TextTemplate("less than [!1]"),
    "-": TextTemplate("difference between [!1] and [!2]"),
    "count": TextTemplate("number of [!1]"),
    "sum": TextTemplate("sum of [!1]"),
    "min": TextTemplate("minimum [!1]"),
    "max": TextTemplate("maximum [!1]"),
    "avg": TextTemplate("average of [!1]"),
    "or": TextTemplate("[!1] or [!2]"),
    "and": TextTemplate("[!1] and [!2]"),
    "number": TextTemplate("[!1]"),
    "lambda": TextTemplate("[!2]"),
    "reverse": TextTemplate("[!1]")
}
reverse_template = TextTemplate("[!1] of [!2]")
juxtaposition_template = TextTemplate("[!1] [!2]")

def generate_explanation(lisptree, lambda_evals = {}):
    if lisptree.is_leaf():
        return lisptree.value
    
    operation_node = lisptree.child(0)
    if operation_node.value == "var":
        if lisptree.child(1).value in lambda_evals:
            return lambda_evals[lisptree.child(1).value]
        else:
            return ""
    elif operation_node.value in text_templates:
        text_template = text_templates[operation_node.value]
        argument_explanations = [generate_explanation(sublisptree, lambda_evals) for sublisptree in lisptree.children[1:]]
        return text_template.text_generator(argument_explanations)
    elif operation_node.is_leaf():
        argument_explanations = [operation_node.value, generate_explanation(lisptree.child(1), lambda_evals)]
        return juxtaposition_template.text_generator(argument_explanations)
    else:
        operation_node_head = operation_node.child(0)
        if operation_node_head.value == "lambda":
            return generate_explanation(operation_node.child(2), {operation_node.child(1).value: generate_explanation(lisptree.child(1))})
        if operation_node_head.value == "reverse":
            argument_explanations = [generate_explanation(operation_node.child(1), lambda_evals), generate_explanation(lisptree.child(1), lambda_evals)]
            return reverse_template.text_generator(argument_explanations)
        return str(lisptree)

def clean_explanation(explanation, context):
    sh_raw = SpecHandler.from_file(context[3], context[5], context[4] + "_0.csv")
    sh = SpecHandler.from_file(context[3], context[5], context[4] + "_0_folded.csv")
    sh.extract_mapping()
    
    explanation = remove_accents(explanation)
    explanation = explanation.strip()
    
    # Examine the chart
    chart_type = None
    primary_field = None
    marks = sh.marks.keys()
    length_field = None
    color_field = None
    if sh.color2data["field"] != None:
        color_field = sh.color2data["field"]

    if "bar" in marks:
        if "xLocation" in sh.vis2data:
            # Vertical bar graph
            if "height" in sh.vis2data:
                length_field = sh.vis2data["height"]
            if "xColumn" in sh.vis2data:
                chart_type = "VGbar"
                primary_field = sh.vis2data["xColumn"]
            elif sh.color2data["field"] != None:
                chart_type = "VSbar"
                primary_field = sh.vis2data["xLocation"]
            else:
                chart_type = "Vbar"
                primary_field = sh.vis2data["xLocation"]
        elif "yLocation" in sh.vis2data:
            # Horizontal bar graph
            if "width" in sh.vis2data:
                length_field = sh.vis2data["width"]
            if "yColumn" in sh.vis2data:
                chart_type = "HGbar"
                primary_field = sh.vis2data["yColumn"]
            elif sh.color2data["field"] != None:
                chart_type = "HSbar"
                primary_field = sh.vis2data["yLocation"]
            else:
                chart_type = "Hbar"
                primary_field = sh.vis2data["yLocation"]
    elif "line" in marks:
        chart_type = "line"
        length_field = sh.vis2data["yLocation"]
        if sh.color2data["field"] != None:
            primary_field = sh.color2data["field"]
        else:
            primary_field = sh.runtime_dtable.fields[0].field_name
    else:
        print("WARNING! UNHANDLED CHART TYPE")
        primary_field = sh.runtime_dtable.fields[0].field_name
    
    # Find out whether the table is folded and if so, establish a link to what is
    # folded
    pivot_field = None
    implicit_field = None
    dummy_fields = []
    field_names_raw = [field.field_name for field in sh_raw.runtime_dtable.fields]
    field_names = [field.field_name for field in sh.runtime_dtable.fields]
            
    # Case in which table is folded
    if set(field_names_raw) != set(field_names):
        preserved_fields = set(field_names_raw) & set(field_names)
        values = []
        for field_name in field_names:
            if field_name in preserved_fields:
                continue
            field_values = [dtable_row.raw_value(field_name) for dtable_row in sh.runtime_dtable.rows]
            values += field_values
        for field_name_raw in field_names_raw:
            field_raw_values = [dtable_row.raw_value(field_name_raw) for dtable_row in sh_raw.runtime_dtable.rows]
            if len(set(field_names) - set(field_raw_values)) == 1 and len(set(field_raw_values) - set(field_names)) == 0:
                pivot_field = field_name_raw
                dummy_fields = [field_name for field_name in field_names if field_name not in preserved_fields]
            elif set(values) - set([""]) == set(field_raw_values) - set([""]):
                implicit_field = field_name_raw

    explanation = re.sub(r"fb:cell\.cell\.\S+ of ", "", explanation)
    
    
    group_counter = 0
    
    cleaned_explanation = ""
    fb_row_header_regex = re.compile("fb:row\.row\.\S+")
    prev_end = 0
    for m in fb_row_header_regex.finditer(explanation):
        last_period_idx = explanation.rfind(".", m.start(), m.end())
        key_words = explanation[last_period_idx + 1 : m.end()].split("_")
        candidate_fields = []
        for dtable_field in sh.runtime_dtable.fields:
            is_matched = True
            for key_word in key_words:
                if key_word.lower() not in remove_accents(dtable_field.field_name).lower():
                    is_matched = False
                    break
            if is_matched:
                candidate_fields.append(dtable_field)
        if len(candidate_fields) == 0:
            continue
        matched_field = min(candidate_fields, key = lambda x: len(x.field_name))
        field_header = ""
        if matched_field.field_name in dummy_fields:
           field_header += "___"
        field_tail = ""
        if length_field != None and "".join(re.compile("[^A-Za-z0-9]").split(length_field)) == "".join(re.compile("[^A-Za-z0-9]").split(matched_field.field_name)):
            field_tail = "L"
            if "V" in chart_type and "bar" in chart_type:
                field_tail += "VB"
            elif "H" in chart_type and "bar" in chart_type:
                field_tail += "HB"
            elif "line" in chart_type:
                field_tail += "LL"
        
        cleaned_explanation += explanation[prev_end : m.start()]
        cleaned_explanation += "(/" + str(group_counter).zfill(3) + "/[[" + field_header + "FIELD" + field_tail + "]]" + matched_field.field_name + "/" + str(group_counter).zfill(3) + "/)"
        prev_end = m.end()
        group_counter += 1
    cleaned_explanation += explanation[prev_end:]

    explanation = cleaned_explanation    

    cleaned_explanation = ""
    fb_cell_value_header_regex = re.compile("fb:cell_[^\.]+\.\S+")
    prev_end = 0
    for m in fb_cell_value_header_regex.finditer(explanation):
        cleaned_explanation += explanation[prev_end : m.start()]
        first_uscore_idx = explanation.find("_", m.start(), m.end())
        period_idx = explanation.find(".", m.start(), m.end())
        field_key_words = explanation[first_uscore_idx + 1 : period_idx].split("_")
        value_str = explanation[period_idx + 1 : m.end()]
        candidate_fields = []
        for dtable_field in sh.runtime_dtable.fields:
            is_matched = True
            for field_key_word in field_key_words:
                if field_key_word not in remove_accents(dtable_field.field_name).lower():
                    is_matched = False
                    break
            if is_matched:
                candidate_fields.append(dtable_field)
        matched_field = min(candidate_fields, key = lambda x: len(x.field_name))

        candidate_cells = []
        for row_idx, dtable_row in enumerate(sh.runtime_dtable.rows):
            test_value = dtable_row.raw_value(matched_field)
            value_key_words = value_str.split("_")
            candidate_fields = []
            is_matched = True
            for value_key_word in value_key_words:
                if value_key_word.lower() not in remove_accents(test_value).lower():
                    is_matched = False
                    break
            if is_matched:
                candidate_cells.append([row_idx, test_value, value_str])

        sorted_candidate_cells = sorted(candidate_cells, key = lambda x: len(x[1]))
        min_length = len(sorted_candidate_cells[0][1])
        candidate_cells = []
        for sorted_candidate_cell in sorted_candidate_cells:
            if len(sorted_candidate_cell[1]) == min_length:
                candidate_cells.append(sorted_candidate_cell)
            else:
                break
                    
        test_values = []
        row_idxs = []
        row_idxs_str = ""
        for candidate_cell in candidate_cells:
            row_idxs_str += str(candidate_cell[0]) + ","
            row_idxs.append(candidate_cell[0])
            test_values.append(candidate_cell[1])
        row_idxs_str = row_idxs_str[:-1]

        value_tail = ""
        if color_field == matched_field.field_name:
            color_value = xcolors.RGBColor.from_hex(sh.color2data["mapping"].inverse[test_values[0]]).to_hsl()
            best_color_name = xcolors.HSLColor.closest_color(color_value)
            color_desc = best_color_name.split(" ")
            if len(color_desc) == 1:
                color_code = "-" + color_codes.inverse[best_color_name]
            elif color_desc[0] == "dark":
                color_code = "D" + color_codes.inverse[color_desc[1]]
            elif color_desc[0] == "light":
                color_code = "L" + color_codes.inverse[color_desc[1]]
            value_tail += "C" + color_code
        cleaned_explanation += "(/" + str(group_counter).zfill(3) + "/[[VALUE" + value_tail + "]]<<" + matched_field.field_name + ">>{" + row_idxs_str + "}" + test_values[0] + "/" + str(group_counter).zfill(3) + "/)"
        group_counter += 1
        prev_end = m.end()
        
    cleaned_explanation += explanation[prev_end:]
    
    explanation = cleaned_explanation
    
    
    explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\)) of (\(\/(?P<gid2>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P=fname)\/(?P=gid2)\/\))", "\g<1>", explanation)
    explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\)) (\(\/(?P<gid2>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P=fname)\/(?P=gid2)\/\))", "\g<1>", explanation)
    explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?FIELD.?.?.?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\) .+) of \(\/(?P<gid2>\d\d\d)\/\[\[.?.?.?FIELD.?.?.?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P=fname)\/(?P=gid2)\/\)", "\g<1>", explanation)
    
    cleaned_explanation = ""
    prev_end = 0
    dummy_field_header_regex = re.compile("\(\/(?P<gid>\d\d\d)\/\[\[___FIELD\]\](.*?)\/(?P=gid)\/\)")
    for m in dummy_field_header_regex.finditer(explanation):
        field_tail = ""
        if length_field != None and "".join(re.compile("[^A-Za-z0-9]").split(length_field)) == "".join(re.compile("[^A-Za-z0-9]").split(implicit_field)):
            field_tail = "L"
            if "V" in chart_type and "bar" in chart_type:
                field_tail += "VB"
            elif "H" in chart_type and "bar" in chart_type:
                field_tail += "HB"
            elif "line" in chart_type:
                field_tail += "LL"
                
        value_tail = ""
        if color_field == pivot_field:

            color_value = xcolors.RGBColor.from_hex(sh.color2data["mapping"].inverse[m.groups()[1]]).to_hsl()
            best_color_name = xcolors.HSLColor.closest_color(color_value)
            color_desc = best_color_name.split(" ")
            if len(color_desc) == 1:
                color_code = "-" + color_codes.inverse[best_color_name]
            elif color_desc[0] == "dark":
                color_code = "D" + color_codes.inverse[color_desc[1]]
            elif color_desc[0] == "light":
                color_code = "L" + color_codes.inverse[color_desc[1]]
            value_tail += "C" + color_code
        cleaned_explanation += explanation[prev_end : m.start()]
        cleaned_explanation += "(/" + str(group_counter).zfill(3) + "/[[***FIELD" + field_tail + "]]" + implicit_field + "/" + str(group_counter).zfill(3) + "/)"
        group_counter += 1
        cleaned_explanation += " of "
        cleaned_explanation += "(/" + str(group_counter).zfill(3) + "/[[___VALUE" + value_tail + "]]<<" + pivot_field + ">>" + m.groups()[1] + "/" + str(group_counter).zfill(3) + "/)"
        prev_end = m.end()
        group_counter += 1
    cleaned_explanation += explanation[prev_end:]
    explanation = cleaned_explanation
    
    explanation = explanation.replace("fb:row.row.index", "[[INDEX]]")
    explanation = explanation.replace("!fb:row.row.next", "[[NEXT]]")
    explanation = explanation.replace("fb:row.row.next", "[[NEXT]]")
    explanation = explanation.replace("fb:type.row", "[[DATA]]")
    explanation = explanation.replace("fb:type.object.type", "")
    explanation = re.sub(r"fb:cell\.cell\.\S+", "", explanation)
    
    explanation = clean_grammatical_junk(explanation)
    
    explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(.+?)\/(?P=gid)\/\)) of \[\[DATA\]\]", "\g<1>", explanation)
    explanation = explanation.replace(" and [[DATA]]", "")
    explanation = explanation.replace("[[NEXT]] [[DATA]]", "[[DATA]] after the [[DATA]]")

    explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\)) with the (smallest|greatest) (\(\/(?P<gid2>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P=fname)\/(?P=gid2)\/\))", "the \g<4> \g<1>", explanation)

    explanation = re.sub(r"\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?FIELD.?.?.?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\) (\(\/(?P<gid2>\d\d\d)\/\[\[.?.?.?VALUE.?.?.?\]\](?:<<(?P=fname)>>)?(?:\{.+?\})?.+?\/(?P=gid2)\/\))", "\g<3>", explanation)
    explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.+?\]\](?:<<.+?>>)?(?:\{.+?\})?(.+?)\/(?P=gid)\/\)) with", "\g<1> of", explanation)
    
    explanation = clean_grammatical_junk(explanation)

    # Determine the type of this explanation
    if explanation[:5] != "meta[":
        explanation = re.sub(r"^(\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?FIELD.?.?.?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\))", "<<RETRIEVE>>\g<1>", explanation)
        explanation = re.sub(r"^(number of)", "<<COUNT>>\g<1>", explanation)
        explanation = re.sub(r"^(sum of)", "<<COMPUTE>>\g<1>", explanation)
        explanation = re.sub(r"^(average of)", "<<COMPUTE>>\g<1>", explanation)
        explanation = re.sub(r"^(difference between)", "<<COMPUTE>>\g<1>", explanation)
        explanation = re.sub(r"^(minimum)", "<<COMPUTE>>\g<1>", explanation)
        explanation = re.sub(r"^(maximum)", "<<COMPUTE>>\g<1>", explanation)
        explanation = re.sub(r"^(the greatest)", "<<COMPUTE>>\g<1>", explanation)
        explanation = re.sub(r"^(the smallest)", "<<COMPUTE>>\g<1>", explanation)
        explanation = re.sub(r"^([^<])", "<<COMPUTE>>\g<1>", explanation)
    
    explanation = re.sub(r"\(\/(?P<gid>\d\d\d)\/\[\[.+?LVB\]\](?:<<.+?>>)?(?:\{.+?\})?.+?\/(?P=gid)\/\)", "the height", explanation)
    explanation = re.sub(r"\(\/(?P<gid>\d\d\d)\/\[\[.+?LHB\]\](?:<<.+?>>)?(?:\{.+?\})?.+?\/(?P=gid)\/\)", "the length", explanation)
    explanation = re.sub(r"\(\/(?P<gid>\d\d\d)\/\[\[.+?LLL\]\](?:<<.+?>>)?(?:\{.+?\})?.+?\/(?P=gid)\/\)", "the height", explanation)
    
    if "bar" in chart_type:
        explanation = explanation.replace("[[DATA]] after the [[DATA]]", "bar after the bar")
        explanation = explanation.replace("[[DATA]]", "bars")
    elif "line" in chart_type:
        explanation = explanation.replace("[[DATA]] after the [[DATA]]", "data point after the data point")
        explanation = explanation.replace("[[DATA]]", "data points")
    
    mark_name = ""
    if chart_type == "line":
        mark_name = "line"
    elif "bar" in chart_type:
        mark_name = "bar"
    elif "line" in chart_type:
        mark_name = "line"
    for color_code in color_codes:
        for color_shade in ["L", "-", "D"]:
            color_regex = re.compile("\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?VALUEC"+ color_shade + color_code + "\]\](?:<<.+?>>)?(?:\{.+?\})?.+?\/(?P=gid)\/\)")
            shade_desc = ""
            if color_shade == "L":
                shade_desc = "light "
            elif color_shade == "D":
                shade_desc = "dark "
            explanation = re.sub(color_regex, "the " + shade_desc + color_codes[color_code] + " " + mark_name, explanation)

    if "bar" in chart_type:
        explanation = re.sub(r"length of (\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?VALUE.?.?.?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\))", "length of the bar for \g<1>", explanation)
        explanation = re.sub(r"height of (\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?VALUE.?.?.?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\))", "height of the bar for \g<1>", explanation)
        explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.*\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\)) of the length", "\g<1> of the bar with length", explanation)
        explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.*\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\)) of the height", "\g<1> of the bar with height", explanation)
        explanation = explanation.replace("greatest the height of the", "tallest")
        explanation = explanation.replace("smallest the height of the", "shortest")
        explanation = explanation.replace("greatest the length of the", "longest")
        explanation = explanation.replace("smallest the length of the", "shortest")
        explanation = explanation.replace("length with", "length of the bar with")
        explanation = explanation.replace("height with", "height of the bar with")
        explanation = explanation.replace("greatest the height", "tallest height")
        explanation = explanation.replace("smallest the height", "shortest height")
        explanation = explanation.replace("greatest the length", "longest length")
        explanation = explanation.replace("smallest the length", "shortest length")
        explanation = explanation.replace("number of the height", "number of bars with height")
        explanation = explanation.replace("number of the length", "number of bars with length")
        explanation = re.sub(r"bar(?: of)? (\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?VALUE.?.?.?\]\](?:<<.+>>)?(?:\{.+?\})?.+?\/(?P=gid)\/\))", "bar for \g<1>", explanation)
    
    if "line" in chart_type:
        explanation = re.sub(r"height of (\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?VALUE.?.?.?\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\))", "height of the line for \g<1>", explanation)
        explanation = re.sub(r"(\(\/(?P<gid>\d\d\d)\/\[\[.*\]\](?:<<.+?>>)?(?:\{.+?\})?(?P<fname>.+?)\/(?P=gid)\/\)) of the height", "\g<1> of the line with height", explanation)
        explanation = explanation.replace("greatest the height of the", "highest")
        explanation = explanation.replace("smallest the height of the", "lowest")
        explanation = explanation.replace("greatest the height", "greatest height")
        explanation = explanation.replace("smallest the height", "smallest height")
        explanation = explanation.replace("number of the height", "number of points with height")
        explanation = re.sub(r"line(?: of)? (\(\/(?P<gid>\d\d\d)\/\[\[.?.?.?VALUE.?.?.?\]\](?:<<.+>>)?(?:\{.+?\})?.+?\/(?P=gid)\/\))", "line for \g<1>", explanation)    

    return explanation
    
results = []
with open('./final_result.csv') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    isFirst = True
    for row in csvreader:
        if isFirst:
            row.append("visual-explanation")
            results.append(row)
            isFirst = False
            continue
        ltree = LispTree.parse_from_string(row[8])
        visual_explanation = add_header_text(remove_references(clean_explanation(generate_explanation(ltree[0]), row)))
        row.append(visual_explanation)

        results.append(row)

with open('./explanation.csv', "w") as outcsvfile:
    csvwriter = csv.writer(outcsvfile, delimiter=',', quotechar='"')
    for result in results:
        csvwriter.writerow(result)