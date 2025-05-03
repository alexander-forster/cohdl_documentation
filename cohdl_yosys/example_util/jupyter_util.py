import cssutils
import xmltodict


def _data_converter(conv_str: str):
    original = conv_str

    if conv_str == "d":
        return ("dec", lambda val: str(int(val, 16)))

    if conv_str.startswith("S"):
        width = int(conv_str[1:])
        limit = 2 ** (width - 1)

        def conv_signed(val):
            val = int(val, 16)

            if val >= limit:
                val -= 2 * limit

            return str(val)

        return ("dec", conv_signed)

    raise AssertionError(f"invalid converter string '{original}'")


def _parse_css_style(css_str: str):
    cp = cssutils.CSSParser(validate=False)
    css_out = cp.parseString(css_str)

    css_classes = {}

    for rule in css_out:
        selector = rule.selectorText

        css_classes[selector.removeprefix(".")] = {
            f"@{property.name}": property.value for property in rule.style
        }

    return css_classes


def _inline_css(root: dict | list, css_classes: dict):
    if isinstance(root, dict):

        if "@class" in root:
            class_name = root["@class"]

            if class_name in css_classes:
                del root["@class"]
                root.update(css_classes[class_name])

        for member in root.values():
            _inline_css(member, css_classes)

    elif isinstance(root, list):
        for elem in root:
            _inline_css(elem, css_classes)


def _find_used_defs(root: dict | list, out: set[str]):
    if isinstance(root, dict):
        for name, member in root.items():
            if name == "@xlink:href":
                out.add(member.removeprefix("#"))

            _find_used_defs(member, out)
    elif isinstance(root, list):
        for elem in root:
            _find_used_defs(elem, out)


def _remove_unused(root: dict):
    used_defs = set()
    _find_used_defs(root, used_defs)

    def_list = root["svg"]["defs"]["g"]
    used_list = []

    for elem in def_list:
        if elem["@id"] in used_defs:
            used_list.append(elem)

    root["svg"]["defs"]["g"] = used_list


def _fix_svg(raw: str):
    # github does not render svg images properly when they contain
    # css styles. This function fixes this by replacing all
    # `class=` attributes with the corresponding properties.
    #
    # Also strips some unused definitions to reduce file size.

    parsed = xmltodict.parse(raw)

    css_classes = _parse_css_style(parsed["svg"]["style"]["#text"])
    del parsed["svg"]["style"]
    _remove_unused(parsed)
    _inline_css(parsed, css_classes)

    result = xmltodict.unparse(parsed)

    return result


def display_vcd(
    glob_path: str, format: str | list[str] | None = None, *, offset=0, top_only=True
):
    """
    Utility function that converts .vcd files to wavedrom and displays
    them in the Jupyer notebook.

    `glob_path` is used to search for vcd files. If multiple matching files
    are found, all are displayed.

    The first `offset` timesteps are removed from the output.

    `format` selects channels to display, defines their order
    and performs some name cleanup. When not set all channels are shown.

    Format syntax:

    For each data channel in the vcd file, this function loops over the
    list of format strings and looks for the first match.
    If no match is found, the channel is deleted.
    All channels are shown ordered by the corresponding format string.

    Format strings can contain the glob character '*' that matches
    arbitrary text and use '|' to separate options.
    When the start of the string is placed in parentheses it is
    removed from the display name.
    When the start of the string is placed in brackets, all
    matching channels are placed in a display group.

    >>> "*axi*"       # matches all names containing axi
    >>>
    >>> "(axi_)*"     # matches all names starting with axi_
    >>>               # and removes the prefix from the display name
    >>>
    >>> "[axi_]*"     # same as last example but all matches
    >>>               # are put in a group named axi_
    >>>
    >>> "[axi=axi_]*" # same as last example but the name of
    >>>               # the group is changed to axi
    >>>
    >>> "[aw=axi_aw]valid|ready" # matches axi_awvalid and axi_awready
    >>>                          # puts found channels in a group named aw
    >>>
    >>> "(axi_)clk|aresetn=reset" # matches axi_clk and axi_reset
    >>>                           # display names are clk and aresetn
    >>>
    >>> "data:d"          # matches 'data' displays values as decimal instead of default hex
    >>> "data:S5"         # matches 'data' displays values as signed int with width 5
    >>> "!internal*"      # matches everything except names starting with internal
    """

    import wavedrom
    import io
    from IPython.display import display, HTML
    import glob
    import json

    import vcd2wavedrom.vcd2wavedrom

    if isinstance(format, str):
        format = [format]

    def base_name(name: str):
        # GHDL adds vectors dimensions to name
        # remove them for consistency with Yosys
        return name.split("[")[0]

    def remove_glob_prefix(glob_str: str, inp: str):
        # remove prefix with optional glob characters
        # from str, returns remaining string
        # or None if the glob pattern does not match

        for nr, part in enumerate(glob_str.split("*")):
            if nr == 0:
                if not inp.startswith(part):
                    return None
                inp = inp.removeprefix(part)
            else:
                pos = inp.find(part)

                if pos == -1:
                    return None

                inp = inp[pos + len(part) :]

        if glob_str.endswith("*"):
            return ""

        return inp

    def search_match(inp_name: str):
        if format is None:
            return ((0, 0), None, inp_name, None)

        for glob_nr, glob_desc in enumerate(format):
            name = inp_name
            bus_name = None

            if "(" in glob_desc:
                assert glob_desc.startswith("(") and glob_desc.count(")") == 1
                assert "[" not in glob_desc and "]" not in glob_desc
                prefix, glob_desc = glob_desc[1:].split(")")

                for prefix_option in prefix.split("|"):
                    name = remove_glob_prefix(prefix_option, inp_name)

                    if name is not None:
                        break

                if name is None:
                    continue

            elif "[" in glob_desc:
                assert glob_desc.startswith("[") and glob_desc.count("]") == 1
                prefix, glob_desc = glob_desc[1:].split("]")

                if "=" in prefix:
                    bus_name, prefix = prefix.split("=")
                else:
                    bus_name = prefix

                for prefix_option in prefix.split("|"):
                    name = remove_glob_prefix(prefix_option, inp_name)

                    if name is not None:
                        break

                if name is None:
                    continue

            for sub_nr, sub_glob in enumerate(glob_desc.split("|")):
                alias = name

                if "=" in sub_glob:
                    alias, sub_glob = sub_glob.split("=")

                data_conv = None

                if ":" in sub_glob:
                    sub_glob, data_conv = sub_glob.split(":")
                    conv_name, data_conv = _data_converter(data_conv)

                    alias = f"{alias}[{conv_name}]"

                ignore = sub_glob.startswith("!")
                sub_glob = sub_glob.removeprefix("!")

                if remove_glob_prefix(sub_glob, name) == "":
                    if ignore:
                        return None

                    return ((glob_nr, sub_nr), bus_name, alias, data_conv)

        return None

    def preprocess_signals(signals: list[dict]):
        collected = []

        for entry in signals:
            name = entry["name"] = base_name(entry["name"])

            search_result = search_match(name)

            if search_result is None:
                continue

            sort_idx, bus_name, name, data_conv = search_result
            entry["name"] = name

            if data_conv is not None:
                entry["data"] = [data_conv(val) for val in entry["data"]]

            collected.append((sort_idx, bus_name, entry))

        collected = sorted(collected, key=lambda x: x[0])

        result = []
        prev_bus_name = None

        for _, bus_name, entry in collected:
            if bus_name is None:
                result.append(entry)
            else:
                if prev_bus_name == bus_name:
                    result[-1].append(entry)
                else:
                    result.append([bus_name, entry])

            prev_bus_name = bus_name

        return result

    for vcd_file in sorted(glob.glob(glob_path, recursive=True)):
        with open(vcd_file) as file:
            print(vcd_file)

            wavedrom_data = vcd2wavedrom.vcd2wavedrom.VCD2Wavedrom(
                {
                    "input_text": file.read(),
                    "top": top_only,
                    # remove initial setup state from wavedrom output
                    "offset": offset,
                }
            ).execute(True)

            wavedrom_data["signal"] = preprocess_signals(wavedrom_data["signal"])

            if len(wavedrom_data["signal"]) == 0:
                print("no channels selected")
                continue

            svg = wavedrom.render(json.dumps(wavedrom_data))

            svg_data = io.StringIO()
            svg.write(svg_data)

            display(
                HTML(
                    f"""
                    <div style="display: flex; justify-content: center; background-color: white;">
                        {_fix_svg(svg_data.getvalue())}
                    </div>
                """
                )
            )
