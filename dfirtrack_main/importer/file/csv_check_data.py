from django.contrib import messages
from dfirtrack_main.logger.default_logger import error_logger, warning_logger

def check_config(request, model):
    """ check variables of dfirtrack.config """

    # reset stop condition
    stop_system_importer_file_csv = False

    # check CSV_COLUMN_SYSTEM for value
    if not 1<= model.csv_column_system <= 256:
        messages.error(request, "`CSV_COLUMN_SYSTEM` is outside the allowed range. Check config!")
        # call logger
        warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_COLUMN_SYSTEM out of range")
        stop_system_importer_file_csv = True

    # check CSV_COLUMN_IP for value
    if not 1<= model.csv_column_ip <= 256:
        messages.error(request, "`CSV_COLUMN_IP` is outside the allowed range. Check config!")
        # call logger
        warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_COLUMN_IP out of range")
        stop_system_importer_file_csv = True

    # create final message and log
    if stop_system_importer_file_csv:
        messages.warning(request, "Nothing was changed.")
        # call logger
        warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_ENDED_WITH_ERRORS")

    return stop_system_importer_file_csv

def check_file(request, rows):
    """ check file for csv respectively some kind of text file """

    # TODO: add check for file containing null bytes (\x00)
    # TODO: add check for empty file (0 bytes)

    try:
        # try to iterate over rows
        for row in rows:
            # do nothing
            pass

        # return True if successful
        return True

    # wrong file type
    except UnicodeDecodeError:
        messages.error(request, "File seems not to be a CSV file. Check file.")
        # call logger
        error_logger(str(request.user), " SYSTEM_IP_IMPORTER_WRONG_FILE_TYPE")
        # return False if not successful
        return False

def check_row(request, row, row_counter, model):
    """ check some values of csv rows """

    # reset continue condition
    continue_system_importer_file_csv = False

    # check system column for empty string
    if not row[model.csv_column_system - 1]:
        messages.error(request, "Value for system in row " + str(row_counter) + " was an empty string. System not created.")
        # call logger
        warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_SYSTEM_COLUMN " + "row_" + str(row_counter) + ":empty_column")
        continue_system_importer_file_csv = True

    # check system column for length of string
    if len(row[model.csv_column_system - 1]) > 50:
        messages.error(request, "Value for system in row " + str(row_counter) + " was too long. System not created.")
        # call logger
        warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_SYSTEM_COLUMN " + "row_" + str(row_counter) + ":long_string")
        continue_system_importer_file_csv = True

    return continue_system_importer_file_csv
