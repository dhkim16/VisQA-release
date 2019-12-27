import json
from bidict import bidict

import utils
import DataTable as dtable

import xcolors

class SpecHandler:
    def __init__(self, dataset_name, spec, runtime_dtable, base_directory = None):
        self.base_directory = base_directory
        self.spec = spec
        self.runtime_dtable = runtime_dtable
        self.vis2data = bidict()
        self.color2data = {"field": None, "mapping": bidict()}
        self.marks = None
        self.xcolors = xcolors.XColor()

        self.extract_marks()
        self.extract_mapping()

    def extract_marks(self):
        # To be really correct, must handle "spec", "repeat", etc., but this should be good enough for the charts we deal with
        self.marks = {}
        encoding_stack = []
        if "encoding" in self.spec:
            encoding_stack.append(self.spec["encoding"])
        if "mark" in self.spec:
            if isinstance(self.spec["mark"], str):
                self.marks[self.spec["mark"]] = encoding_stack[-1]
            else:
                self.marks[self.spec["mark"]["type"]] = encoding_stack[-1]

        if "layer" in self.spec:
            for layer in self.spec["layer"]:
                if "encoding" in layer:
                    encoding_stack.append(layer["encoding"])
                if "mark" in self.spec:
                    if isinstance(self.spec["mark"], str):
                        self.marks[self.spec["mark"]] = utils.merge_dicts(encoding_stack)
                    else:
                        self.marks[self.spec["mark"]["type"]] = utils.merge_dicts(encoding_stack)
                if "encoding" in layer:
                    encoding_stack.pop()
    
    def extract_mapping(self):
        # We ignore transformations for now, but if it becomes important, may have to implement
        if "bar" in self.marks:
            raw_mapping = self.marks["bar"]

            if not ("x" in raw_mapping and "y" in raw_mapping):
                # Either x or y is missing. Something is probably wrong with spec
                raise ValueError("Invalid bar spec file: missing x or y")

            domain_exclusion = None
            if raw_mapping["x"]["type"] == "quantitative" and raw_mapping["y"]["type"] != "quantitative":
                # Horizontal bar graph
                if "x2" in raw_mapping:
                    # A horizontal band graph
                    pass
                elif "row" in raw_mapping:
                    # A grouped horizontal bar graph
                    if "field" in raw_mapping["row"]:
                        self.vis2data["yRow"] = raw_mapping["row"]["field"]
                        domain_exclusion = raw_mapping["row"]["field"]
                    else:
                        pass

                    if "field" in raw_mapping["y"]:
                        self.vis2data["height"] = raw_mapping["y"]["field"]
                    else:
                        pass
                    if "field" in raw_mapping["x"]:
                        self.vis2data["xLocation"] = raw_mapping["x"]["field"]
                    else:
                        pass
                else:
                    # A regular horizontal bar graph
                    if "field" in raw_mapping["x"]:
                        self.vis2data["width"] = raw_mapping["x"]["field"]
                    else:
                        pass
                    if "field" in raw_mapping["y"]:
                        self.vis2data["yLocation"] = raw_mapping["y"]["field"]
                        domain_exclusion = raw_mapping["y"]["field"]
                    else:
                        pass

            elif raw_mapping["y"]["type"] == "quantitative" and raw_mapping["x"]["type"] != "quantitative":
                # Vertical bar graph
                if "y2" in raw_mapping:
                    # A vertical band graph
                    pass
                elif "column" in raw_mapping:
                    # A grouped vertical bar graph
                    if "field" in raw_mapping["column"]:
                        self.vis2data["xColumn"] = raw_mapping["column"]["field"]
                        domain_exclusion = raw_mapping["column"]["field"]
                    else:
                        pass

                    if "field" in raw_mapping["y"]:
                        self.vis2data["height"] = raw_mapping["y"]["field"]
                    else:
                        pass
                    if "field" in raw_mapping["x"]:
                        self.vis2data["xLocation"] = raw_mapping["x"]["field"]
                    else:
                        pass
                else:
                    # A regular vertical bar graph
                    if "field" in raw_mapping["y"]:
                        self.vis2data["height"] = raw_mapping["y"]["field"]
                    else:
                        pass
                    if "field" in raw_mapping["x"]:
                        self.vis2data["xLocation"] = raw_mapping["x"]["field"]
                        domain_exclusion = raw_mapping["x"]["field"]
                    else:
                        pass

            if "color" in raw_mapping and "field" in raw_mapping["color"]:
                self.color2data["field"] = raw_mapping["color"]["field"]
                if "scale" in raw_mapping["color"]:
                    if raw_mapping["color"]["scale"] == None:
                        # Here, the color of bar matches the axis value, so no need for conversion
                        pass
                    elif "range" in raw_mapping["color"]["scale"] and "domain" in raw_mapping["color"]["scale"]:
                        for elem_idx in range(len(raw_mapping["color"]["scale"]["domain"])):
                            self.color2data["mapping"][raw_mapping["color"]["scale"]["range"][elem_idx]] = raw_mapping["color"]["scale"]["domain"][elem_idx]
                    elif "range" in raw_mapping["color"]["scale"]:
                        domain = []
                        for row in self.runtime_dtable.rows:
                            field_value = row.raw_value(raw_mapping["color"]["field"])

                            if field_value == None:
                                continue

                            if not field_value in domain:
                                domain.append(field_value)

                        if len(domain) == 0:
                            # The table is 'folded'
                            for field in self.runtime_dtable.fields:
                                if field.field_name != domain_exclusion:
                                    domain.append(field.field_name)

                        domain = sorted(domain)
                        for elem_idx in range(len(raw_mapping["color"]["scale"]["range"])):
                            self.color2data["mapping"][raw_mapping["color"]["scale"]["range"][elem_idx]] = domain[elem_idx]
                    else: # scheme set?
                        pass
                else:
                    domain = []
                    for row in self.runtime_dtable.rows:
                        field_value = row.raw_value(raw_mapping["color"]["field"])

                        if field_value == None:
                                continue

                        if not field_value in domain:
                            domain.append(field_value)


                    if len(domain) == 0:
                        # The table is 'folded'
                        for field in self.runtime_dtable.fields:
                            if field.field_name != domain_exclusion:
                                domain.append(field.field_name)
                    if not("color" in raw_mapping and "sort" in raw_mapping["color"] and raw_mapping["color"]["sort"] == None):
                        domain = sorted(domain)
                    color_range = ["#4c78a8", "#f58518", "#e45756", "#72b7b2", "#54a24b", "#eeca3b", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac"]
                    for elem_idx in range(len(domain)):
                        self.color2data["mapping"][color_range[elem_idx]] = domain[elem_idx]
                # TODO: ADD ADDITIONAL NAMING?
                # for field_value in self.color2data["mapping"]:
                #     color_hex = self.color2data[field_value]
                #     for color_name in self.xcolors:



        if "circle" in self.marks:
            raw_mapping = self.marks["circle"]

            if not ("x" in raw_mapping and "y" in raw_mapping):
                # Either x or y is missing. Something is probably wrong with spec
                raise ValueError("Invalid point spec file: missing x or y")

            if "field" in raw_mapping["x"]:
                self.vis2data["xLocation"] = raw_mapping["x"]["field"]
            else:
                pass
            if "field" in raw_mapping["y"]:
                self.vis2data["yLocation"] = raw_mapping["y"]["field"]
            else:
                pass

            if "size" in raw_mapping:
                if "field" in raw_mapping["size"]:
                    self.vis2data["size"] = raw_mapping["size"]["field"]
                else:
                    pass


            if "color" in raw_mapping and "field" in raw_mapping["color"]:
                self.color2data["field"] = raw_mapping["color"]["field"]
                if "scale" in raw_mapping["color"]:
                    if raw_mapping["color"]["scale"] == None:
                        # Here, the color of bar matches the axis value, so no need for conversion
                        pass
                    elif "range" in raw_mapping["color"]["scale"] and "domain" in raw_mapping["color"]["scale"]:
                        for elem_idx in range(len(raw_mapping["color"]["scale"]["domain"])):
                            self.color2data["mapping"][raw_mapping["color"]["scale"]["range"][elem_idx]] = raw_mapping["color"]["scale"]["domain"][elem_idx]
                    elif "range" in raw_mapping["color"]["scale"]:
                        domain = []
                        for row in self.runtime_dtable.rows:
                            field_value = row.raw_value(raw_mapping["color"]["field"])
                            if not field_value in domain:
                                domain.append(field_value)
                        domain = sorted(domain)
                        for elem_idx in range(len(raw_mapping["color"]["scale"]["range"])):
                            self.color2data["mapping"][raw_mapping["color"]["scale"]["range"][elem_idx]] = domain[elem_idx]
                    else: # scheme set?
                        pass
                else:
                    domain = []
                    for row in self.runtime_dtable.rows:
                        field_value = row.raw_value(raw_mapping["color"]["field"])
                        if not field_value in domain:
                            domain.append(field_value)
                    domain = sorted(domain)
                    color_range = ["#4c78a8", "#f58518", "#e45756", "#72b7b2", "#54a24b", "#eeca3b", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac"]
                    for elem_idx in range(len(domain)):
                        self.color2data["mapping"][color_range[elem_idx]] = domain[elem_idx]

        if "line" in self.marks:
            raw_mapping = self.marks["line"]

            if not ("x" in raw_mapping and "y" in raw_mapping):
                # Either x or y is missing. Something is probably wrong with spec
                raise ValueError("Invalid line spec file: missing x or y")

            if raw_mapping["y"]["type"] != "quantitative":
                # Both x and y must be quantitative ?!
                raise ValueError("Invalid line spec file: y is not quantitative")

            if "field" in raw_mapping["x"]:
                self.vis2data["xLocation"] = raw_mapping["x"]["field"]
            else:
                pass
            if "field" in raw_mapping["y"]:
                self.vis2data["yLocation"] = raw_mapping["y"]["field"]
            else:
                pass

            if "color" in raw_mapping and "field" in raw_mapping["color"]:
                self.color2data["field"] = raw_mapping["color"]["field"]
                if "scale" in raw_mapping["color"]:
                    if raw_mapping["color"]["scale"] == None:
                        # Here, the color of bar matches the axis value, so no need for conversion
                        pass
                    elif "range" in raw_mapping["color"]["scale"] and "domain" in raw_mapping["color"]["scale"]:
                        for elem_idx in range(len(raw_mapping["color"]["scale"]["domain"])):
                            self.color2data["mapping"][raw_mapping["color"]["scale"]["range"][elem_idx]] = raw_mapping["color"]["scale"]["domain"][elem_idx]
                    elif "range" in raw_mapping["color"]["scale"]:
                        domain = []
                        for row in self.runtime_dtable.rows:
                            field_value = row.raw_value(raw_mapping["color"]["field"])
                            if not field_value in domain:
                                domain.append(field_value)
                        domain = sorted(domain)
                        for elem_idx in range(len(raw_mapping["color"]["scale"]["range"])):
                            self.color2data["mapping"][raw_mapping["color"]["scale"]["range"][elem_idx]] = domain[elem_idx]
                    else: # scheme set?
                        pass
                else:
                    domain = []
                    for row in self.runtime_dtable.rows:
                        field_value = row.raw_value(raw_mapping["color"]["field"])
                        if not field_value in domain:
                            domain.append(field_value)
                    domain = sorted(domain)
                    color_range = ["#4c78a8", "#f58518", "#e45756", "#72b7b2", "#54a24b", "#eeca3b", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac"]
                    for elem_idx in range(len(domain)):
                        self.color2data["mapping"][color_range[elem_idx]] = domain[elem_idx]

        if "point" in self.marks:
            raw_mapping = self.marks["point"]

            if not ("x" in raw_mapping and "y" in raw_mapping):
                # Either x or y is missing. Something is probably wrong with spec
                raise ValueError("Invalid point spec file: missing x or y")

            if raw_mapping["x"]["type"] != "quantitative" or raw_mapping["y"]["type"] != "quantitative":
                # Both x and y must be quantitative ?!
                raise ValueError("Invalid point spec file: x or y is not quantitative")


            if "field" in raw_mapping["x"]:
                self.vis2data["xLocation"] = raw_mapping["x"]["field"]
            else:
                pass
            if "field" in raw_mapping["y"]:
                self.vis2data["yLocation"] = raw_mapping["y"]["field"]
            else:
                pass


            if "color" in raw_mapping and "field" in raw_mapping["color"]:
                self.color2data["field"] = raw_mapping["color"]["field"]
                if "scale" in raw_mapping["color"]:
                    if raw_mapping["color"]["scale"] == None:
                        # Here, the color of bar matches the axis value, so no need for conversion
                        pass
                    elif "range" in raw_mapping["color"]["scale"] and "domain" in raw_mapping["color"]["scale"]:
                        for elem_idx in range(len(raw_mapping["color"]["scale"]["domain"])):
                            self.color2data["mapping"][raw_mapping["color"]["scale"]["range"][elem_idx]] = raw_mapping["color"]["scale"]["domain"][elem_idx]
                    elif "range" in raw_mapping["color"]["scale"]:
                        domain = []
                        for row in self.runtime_dtable.rows:
                            field_value = row.raw_value(raw_mapping["color"]["field"])
                            if not field_value in domain:
                                domain.append(field_value)
                        domain = sorted(domain)
                        for elem_idx in range(len(raw_mapping["color"]["scale"]["range"])):
                            self.color2data["mapping"][raw_mapping["color"]["scale"]["range"][elem_idx]] = domain[elem_idx]
                    else: # scheme set?
                        pass
                else:
                    domain = []
                    for row in self.runtime_dtable.rows:
                        field_value = row.raw_value(raw_mapping["color"]["field"])
                        if not field_value in domain:
                            domain.append(field_value)
                    domain = sorted(domain)
                    color_range = ["#4c78a8", "#f58518", "#e45756", "#72b7b2", "#54a24b", "#eeca3b", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac"]
                    for elem_idx in range(len(domain)):
                        self.color2data["mapping"][color_range[elem_idx]] = domain[elem_idx]




    @classmethod
    def from_file(cls, dataset_name, spec_file_name, runtime_file_name, base_directory = None):
        spec_file_name = "data/" + dataset_name + "/specs/" + spec_file_name
        runtime_file_name = "data/" + dataset_name + "/runtime-data/" + runtime_file_name

        if base_directory != None:
            spec_file_name = base_directory + spec_file_name
            runtime_file_name = base_directory + runtime_file_name

        with open(spec_file_name) as spec_file:
            spec = json.load(spec_file)

        runtime_dtable = dtable.DataTable.from_file(runtime_file_name)

        return cls(dataset_name, spec, runtime_dtable, base_directory)