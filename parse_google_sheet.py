import argparse
from datetime import datetime
import logging
import math
import numbers
import os
import pandas
import requests
import sys
import yaml


def parse_args() -> dict:
    """Function to parse script arguments"""
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-vv", "--debug", action="store_true", help="debug output")
    parser.add_argument(
        "-sid",
        "--sheetid",
        type=str,
        default="1guvefLTrWjY3B1BQNK_NWsy-MceHCnrjjZjT46-jqmw",
        help="Google Spreadsheet ID",
    )
    parser.add_argument(
        "-sname",
        "--sheetname",
        type=str,
        required=True,
        help="Google Spreadsheet Name",
    )
    args = parser.parse_args()
    return args


def getGoogleSeet(spreadsheet_id, sheet_name, outDir, outFile):

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    response = requests.get(url)
    print(response)
    if response.status_code == 200:
        filepath = os.path.join(outDir, outFile)
        with open(filepath, "wb") as f:
            f.write(response.content)
        print("CSV file saved to: {}".format(filepath))
    else:
        print(f"Error downloading Google Sheet: {response.status_code}")
        sys.exit(1)

    return filepath


def is_nan(entry):
    if isinstance(entry, numbers.Number) and math.isnan(entry):
        return True
    else:
        return False


def export_to_yml(filepath):
    conferences_csv = pandas.read_csv(filepath)

    with open("_data/conferences.yml") as stream:
        try:
            conferences_yml = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            logging.error(e)

    conferences = set()
    if not conferences_yml:
        conferences_yml = []

    for entry in conferences_yml:
        conferences.add(entry["id"])

    logging.debug(conferences_yml)
    logging.debug(conferences_csv.iloc[:, 1:16])

    for _, row in conferences_csv.iterrows():
        for i, entry in enumerate(conferences_yml):
            if entry["id"] == row["id"]:
                logging.warning(f"Deleting entry {entry['id']}")
                del conferences_yml[i]
                break

        # Check validity of entries
        for entry in row.keys():
            if is_nan(row[entry]):
                row[entry] = None

        # Check if deadline date(s) are estimated
        if "EST" in row:
            estimated = row["EST"]

        if "Timezone" not in row:
            estimated = True

        # TODO add more criteria?

        # Validate dates
        dates = {}
        for datekey in ["DL", "DL Abstract", "Conf start", "Conf end"]:
            if not isinstance(row[datekey], str):
                date = "01.01.1900"  # invalid data set to Jan 1, 1900
            else:
                date = row[datekey]

            dates[datekey] = datetime.strptime(date, "%d.%m.%Y")

        # create tags
        subs = []
        if row["Main topic"]:
            subs.append(row["Main topic"])
        if row["Other topics"]:
            subs.extend(row["Other topics"].split(", "))

        track = f" [{row['Track']}]" if row["Track"] else ""

        # Write info
        conferences_yml.append(
            {
                "title": row["Conference"] + track,
                "year": None,
                "id": row["id"],
                "full_name": row["Conference"] + track,
                "link": row["Call"],
                "deadline": dates["DL"].strftime("%Y-%m-%d"),
                "abstract_deadline": dates["DL Abstract"].strftime("%Y-%m-%d"),
                "timezone": "UTC-12",
                "estimated": estimated,
                "place": row["Location"],
                "date": f"{dates['Conf start'].strftime("%d %B")} - {dates['Conf end'].strftime(
                    "%d %B, %Y"
                )}",
                "start": dates["Conf start"].strftime("%Y-%m-%d"),
                "end": dates["Conf end"].strftime("%Y-%m-%d"),
                "paperslink": None,
                "pwclink": None,
                "hindex": None,
                "CORE": row["CORE23"],
                "sub": subs,
                "note": None,
            }
        )

    return conferences_yml


def main() -> int:
    """main function"""
    # load arguments
    args = parse_args()

    # define logging level and format
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s %(levelname)s:%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=level,
    )

    os.makedirs("_temp", exist_ok=True)
    filepath = getGoogleSeet(args.sheetid, args.sheetname, "_temp", "conferences.csv")
    conferences_yml = export_to_yml(filepath)

    with open("_data/conferences.yml", "w") as file:
        yaml.dump(conferences_yml, file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
