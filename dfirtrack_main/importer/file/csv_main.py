import csv
from django.contrib import messages
from django.utils import timezone
from dfirtrack_config.models import SystemImporterFileCsvConfigModel
from dfirtrack_main.importer.file.csv_add_attributes import add_fk_attributes, add_many2many_attributes, create_lock_tags
from dfirtrack_main.importer.file.csv_run_checks import run_check_content_file_type
from dfirtrack_main.importer.file.csv_messages import final_messages
from dfirtrack_main.logger.default_logger import info_logger, warning_logger
from dfirtrack_main.models import System
from io import TextIOWrapper


def system_handler(request=None, uploadfile=False):

    # get config model
    model = SystemImporterFileCsvConfigModel.objects.get(system_importer_file_csv_config_name = 'SystemImporterFileCsvConfig')

    """ start system importer """

    # if function was called from 'system_instant' and 'system_upload'
    if request:
        # get user
        csv_import_user = request.user
    # if function was called from 'system_cron'
    else:
        # get user
        csv_import_user = model.csv_import_username

    # call logger
    info_logger(csv_import_user.username, " SYSTEM_IMPORTER_FILE_CSV_CRON_BEGAN")

    # create lock tags
    create_lock_tags(model)

    """ file handling  """

    # file was uploaded via form (called via 'system_upload')
    if uploadfile:
        # text object can not be passed as argument from 'system_upload'
        systemcsv = TextIOWrapper(request.FILES['systemcsv'].file, encoding=request.encoding)
    # file was fetched from file system (called via 'system_instant' or 'system_cron')
    else:
        # build csv file path
        csv_import_file = model.csv_import_path + '/' + model.csv_import_filename
        # open file
        systemcsv = open(csv_import_file, 'r')

    # get field delimiter from config
    if model.csv_field_delimiter == 'field_comma':
        delimiter = ','
    elif model.csv_field_delimiter == 'field_semicolon':
        delimiter = ';'

    # get text quotechar from config
    if model.csv_text_quote == 'text_double_quotation_marks':
        quotechar = '"'
    elif model.csv_text_quote == 'text_single_quotation_marks':
        quotechar = "'"

    # read rows out of csv
    rows = csv.reader(systemcsv, delimiter=delimiter, quotechar=quotechar)

    """ check file """

    # check file for csv respectively some kind of text file
    file_check = run_check_content_file_type(rows, csv_import_user.username)

    # if function was called from 'system_instant' and 'system_upload'
    if not file_check and request:
        # call message
        messages.error(request, "File seems not to be a CSV file. Check file!")
    # TODO: [messages] call message if function was called from 'system_cron' for all users?
    # TODO: [messages] should work with 'async_messages'
    elif not file_check and not request:
        pass

    # leave system_importer_file_csv if file check throws errors
    if not file_check:
        # close file
        systemcsv.close()
        # return to calling function
        return

    # jump to begin of file again after iterating in file check
    systemcsv.seek(0)

    """ prepare and start loop """

    # set row_counter (needed for logger)
    row_counter = 1

    # set systems_created_counter (needed for logger)
    systems_created_counter = 0

    # set systems_updated_counter (needed for logger)
    systems_updated_counter = 0

    # set systems_multiple_counter (needed for logger)
    systems_multiple_counter = 0

    # set systems_skipped_counter (needed for logger)
    systems_skipped_counter = 0

    # iterate over rows
    for row in rows:

        # TODO: [config] csv_check_data.run_check_content_attributes
        # TODO: [config] check configured fields in row for valid values
        # TODO: [config] either called from here or directly from attribute functions
        # TODO: [config] some checks might be called from 'add_fk_attributes' or 'add_many2many_attributes'

        """ skip headline if necessary """

        # check for first row and headline condition
        if row_counter == 1 and model.csv_headline:
            # autoincrement row counter
            row_counter += 1
            # leave loop for headline row
            continue

        """ filter for systems """

        # get system name (for domain name comparison)
        system_name = row[model.csv_column_system - 1]

        # TODO: [logic] add option which attributes are used for filtering?
        # TODO: [logic] (like domain, dnsname, company)
        # TODO: [logic] e.g. 'csv_identification_dnsname'

        # get all systems
        systemquery = System.objects.filter(
            system_name = system_name,
        )

        """ check how many systems were returned """

        # if there is only one system -> modify system
        if len(systemquery) == 1:

            # skip if system already exists (depending on csv_skip_existing_system)
            if model.csv_skip_existing_system:

                # autoincrement counter
                systems_skipped_counter += 1
                # autoincrement row counter
                row_counter += 1
                # leave loop
                continue

            # TODO: [logic] add option which attributes are used for filtering?
            # TODO: [logic] (like domain, dnsname, company)
            # TODO: [logic] e.g. 'csv_identification_dnsname'

            # get existing system object
            system = System.objects.get(
                system_name=system_name,
            )

            # change mandatory meta attributes
            system.system_modify_time = timezone.now()
            system.system_modified_by_user_id = csv_import_user

            # set value for already existing system (modify system)
            system_created = False

            # add foreign key relationships to system
            system = add_fk_attributes(system, system_created, model, row)

            # save object
            system.save()

            # add many2many relationships to system
            system = add_many2many_attributes(system, system_created, model, row)

            # autoincrement systems_updated_counter
            systems_updated_counter += 1

            # call logger
            system.logger(csv_import_user.username, " SYSTEM_IMPORTER_FILE_CSV_CRON_SYSTEM_MODIFIED")

        # if there is more than one system
        elif len(systemquery) > 1:

            # TODO: [messages] add list with system_name for message
            # TODO: [messages] systems_multiple_list
            # TODO: [messages] call message at the end
            # TODO: [messages] one message for all system names

            # autoincrement systems_multiple_counter
            systems_multiple_counter += 1

            # call logger
            warning_logger(csv_import_user.username, " SYSTEM_IMPORTER_FILE_CSV_CRON_MULTIPLE_SYSTEMS " + "System:" + system_name)

        # if there is no system -> create system
        else:

            # create new system object
            system = System()

            # add system_name from csv
            system.system_name = system_name

            # add mandatory meta attributes
            system.system_modify_time = timezone.now()
            system.system_created_by_user_id = csv_import_user
            system.system_modified_by_user_id = csv_import_user

            # set value for new system (create system)
            system_created = True

            # add foreign key relationships to system
            system = add_fk_attributes(system, system_created, model, row)

            # save object
            system.save()

            # add many2many relationships to system
            system = add_many2many_attributes(system, system_created, model, row)

            # autoincrement systems_created_counter
            systems_created_counter += 1

            # call logger
            system.logger(csv_import_user.username, " SYSTEM_IMPORTER_FILE_CSV_CRON_SYSTEM_CREATED")

        # autoincrement row counter
        row_counter += 1

    # close file
    systemcsv.close()

    # if function was called from 'system_instant' and 'system_upload'
    if request:
        # TODO: [messages] show message with multiple systems
        # TODO: [messages] systems_multiple_list
        # call final messages
        final_messages(request, systems_created_counter, systems_updated_counter, systems_skipped_counter, systems_multiple_counter)
    # TODO: [messages] call message if function was called from 'system_cron' for all users?
    # TODO: [messages] should work with 'async_messages'
    else:
        pass

    # call logger
    info_logger(csv_import_user.username, " SYSTEM_IMPORTER_FILE_CSV_CRON_STATUS " + "created:" + str(systems_created_counter) + "|" + "updated:" + str(systems_updated_counter) + "|" + "skipped:" + str(systems_skipped_counter) + "|" + "multiple:" + str(systems_multiple_counter))
    info_logger(csv_import_user.username, " SYSTEM_IMPORTER_FILE_CSV_CRON_END")

    # return to calling function
    return