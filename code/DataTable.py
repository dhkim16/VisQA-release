import csv

class DataField:
    UNKNOWN = -1
    NOMINAL = 0
    ORDINAL = 1
    QUANTITATIVE = 2
    FIELD_TYPES = {
        UNKNOWN: "unknown",
        NOMINAL: "nominal",
        ORDINAL: "ordinal",
        QUANTITATIVE: "quantitative"
    }

    def __init__(self, field_type, field_name, first_entry = None):
        self.field_type = field_type
        self.field_name = field_name
        self.first_entry = first_entry # Use if want to rank by data field

class DataEntry:
    def __init__(self, field, value):
        '''
        Construct a data entry

        :param field: should be a DataField object
        :param value:
        :return: returns nothing
        '''
        self.field = field
        self.value = value

class DataRow:
    def __init__(self, fields, values, prev_row = None, next_row = None):
        self.fields = fields
        self.entries = {}
        for field_idx, field in enumerate(fields):
            self.entries[field.field_name] = DataEntry(field, values[field_idx])
        self.prev_row = prev_row
        self.next_row = next_row

    def raw_value(self, field = None):
        if field == None:
            #TODO: TAKE THE FIRST NONE-QUANTITATIIVE
            # if len(self.fields) != 1:
            #     raise ValueError("To obtain raw value of a row, it should only have 1 field")
            obtained_value = self.entries[self.fields[0].field_name].value
        elif isinstance(field, str): # Python3 (Python2 should use basestring)
            if field in self.entries:
                obtained_value = self.entries[field].value
            else:
                return None
        else:
            if field.field_name in self.entries:
                obtained_value = self.entries[field.field_name].value
            else:
                return None
        return obtained_value

    def value(self, field):
        return self.create_temporary_row(field, self.raw_value(field))

    def _value(self, args):
        return self.value(args["field"])

    def get_prev_row(self):
        return self.prev_row

    def _get_prev_row(self, args):
        return self.get_prev_row()

    def get_next_row(self):
        return self.next_row

    def _get_next_row(self, args):
        return self.get_next_row()

    def __str__(self):
        row_desc = ""
        for field in self.fields:
            row_desc += "(" + field.field_name + ": " + str(self.entries[field.field_name].value) + "), "
        return row_desc

    dispatch_map = {
        "value": {
            "function": _value,
            "required_params": ["field"],
            "optional_params": []
        },
        "get_prev_row": {
            "function": _get_prev_row,
            "required_params": [],
            "optional_params": []
        },
        "get_next_row": {
            "function": _get_next_row,
            "required_params": [],
            "optional_params": []
        }
    }
    def dispatch(self, function_name, args):
        bound = self.dispatch_map[function_name]["function"].__get__(self, type(self))
        return bound(args)

    @staticmethod
    def create_temporary_row(field, value):
        if isinstance(field, str): # Python3 (Python2 should use basestring)
            field = DataField(DataField.UNKNOWN, field)
        return DataRow([field], [value])

    @staticmethod
    def diff_field(row1, row2, field):
        return DataRow.create_temporary_row(field, row1.raw_value(field) - row2.raw_value(field))

    @staticmethod
    def _diff_field(args):
        return DataRow.diff_field(args["row1"], args["row2"], args["field"])

    static_dispatch_map = {
        "diff_field": {
            "function": _diff_field,
            "required_params": ["row1", "row2", "field"],
            "optional_params": []
        }
    }

    @staticmethod
    def static_dispatch(function_name, args):
        bound = DataRow.static_dispatch_map[function_name]["function"].__get__(DataRow, type(DataRow))
        return bound(args)


class DataRows:
    def __init__(self, fields, rows):
        self.fields = fields
        self.rows = rows

    def count(self):
        return DataRow.create_temporary_row("count", len(self.rows))

    def _count(self, args):
        return self.count()

    def sum_field(self, field):
        total = 0
        for row in self.rows:
            total += row.raw_value(field)
        return DataRow.create_temporary_row(field, total)

    def _sum_field(self, args):
        return self.sum_field(args["field"])

    def mean_field(self, field):
        total = 0
        for row in self.rows:
            total += row.raw_value(field)
        return DataRow.create_temporary_row(field, total / float(len(self.rows)))

    def _mean_field(self, args):
        return self.mean_field(args["field"])

    def rank_K_field(self, field, K):
        # CAUTION: Rank is 1-based, so there is a -1.
        return sorted(self.rows, key = lambda row: row.raw_value(field), reverse = True)[K - 1]

    def _rank_K_field(self, args):
        return self.rank_K_field(args["field"], args["K"])

    def rev_rank_K_field(self, field, K):
        # CAUTION: Rank is 1-based, so there is a -1.
        return sorted(self.rows, key = lambda row: -row.raw_value(field), reverse = True)[K - 1]

    def _rev_rank_K_field(self, args):
        return self.rev_rank_K_field(args["field"], args["K"])

    def max_field(self, field):
        return self.rank_K_field(field, 1)

    def _max_field(self, args):
        return self.max_field(args["field"])

    def min_field(self, field):
        return self.rev_rank_K_field(field, 1)

    def _min_field(self, args):
        return self.min_field(args["field"])

    # Usage note: count string occurance first!
    def search_string_row(self, str_data):
        for row in self.rows:
            for field in self.fields:
                if isinstance(row.raw_value(field), str) and row.raw_value(field).lower() == str_data.lower():
                    return row
        
    def _search_string_row(self, args):
        return self.search_string_row(args["str_data"])

    # Usage note: count string occurance first!
    def search_string_rows(self, str_data):
        matched_rows = []
        for row in self.rows:
            for field in self.fields:
                if isinstance(row.raw_value(field), str) and row.raw_value(field).lower() == str_data.lower():
                    matched_rows.append(row)
        return DataRows(self.fields, matched_rows)
        
    def _search_string_rows(self, args):
        return self.search_string_rows(args["str_data"])


    def filter_numerical(self, min_value = float('-inf'), min_inclusive = False, max_value = float('inf'), max_inclusive = False):
        pass

    def _filter_numerical(self, args):
        pass

    dispatch_map = {
        "count": {
            "function": _count,
            "required_params": [],
            "optional_params": []
        },
        "sum_field": {
            "function": _sum_field,
            "required_params": ["field"],
            "optional_params": []
        },
        "mean_field": {
            "function": _mean_field,
            "required_params": ["field"],
            "optional_params": []
        },
        "rank_K_field": {
            "function": _rank_K_field,
            "required_params": ["field", "k"],
            "optional_params": []
        },
        "rev_rank_K_field": {
            "function": _rev_rank_K_field,
            "required_params": ["field", "k"],
            "optional_params": []
        },
        "max_field": {
            "function": _max_field,
            "required_params": ["field"],
            "optional_params": []
        },
        "min_field": {
            "function": _min_field,
            "required_params": ["field"],
            "optional_params": []
        },
        "search_string_row": {
            "function": _search_string_row,
            "required_params": ["str_data"],
            "optional_params": []
        },
        "search_string_rows": {
            "function": _search_string_rows,
            "required_params": ["str_data"],
            "optional_params": []
        },
    }
    def dispatch(self, function_name, args):
        bound = self.dispatch_map[function_name]["function"].__get__(self, type(self))
        return bound(args)

    def count_string_occurance(self, str_data):
        match_count = 0
        for row in self.rows:
            for field in self.fields:
                if isinstance(row.raw_value(field), str) and row.raw_value(field).lower() == str_data.lower():
                    match_count += 1
        return match_count

    def __str__(self):
        rows_desc = ""
        for field in self.fields:
            rows_desc += field.field_name + "\t"
        rows_desc += "\n"
        for row in self.rows:
            for field in self.fields:
                rows_desc += str(row.entries[field.field_name].value) + "\t"
            rows_desc += "\n"
        return rows_desc

class DataTable(DataRows):
    def __init__(self, fields, rows):
        DataRows.__init__(self, fields, rows)

    @classmethod
    def from_table(cls, table):
        fields = []
        for field_name in table[0]:
            fields.append(DataField(DataField.UNKNOWN, field_name))
        rows = []
        prev_row = None
        for table_row in table[1:]:
            curr_row = DataRow(fields, table_row, prev_row)
            if prev_row != None:
                prev_row.next_row = curr_row
            prev_row = curr_row
            rows.append(curr_row)
        return cls(fields, rows)

    @classmethod
    def from_file(cls, file_name, file_type = "auto"):
        if file_type == "auto":
            file_type = file_name.split(".")[-1].lower()

        if file_type == "csv":
            raw_table = []
            with open(file_name, newline = '') as csv_file:
                csv_reader = csv.reader(csv_file, quotechar='"', escapechar='\\')
                for csv_row in csv_reader:
                    raw_table.append(csv_row)
        elif file_type == "tsv":
            pass
        else:
            raise ValueError("Invalid or unhandled file type")
        
        return cls.from_table(raw_table)


