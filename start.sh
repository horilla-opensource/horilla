#!/bin/bash

# Check if all required environment variables are set
if [ -z "$FIRST_NAME" ] || [ -z "$LAST_NAME" ] || [ -z "$USERNAME" ] || \
   [ -z "$PASSWORD" ] || [ -z "$EMAIL" ] || [ -z "$PHONE" ] || [ -z "$SECRET_KEY" ] || [ -z "$URL" ]; then
    echo "One or more required environment variables are missing."
    echo "Make sure FIRST_NAME, LAST_NAME, USERNAME, PASSWORD, EMAIL, PHONE, SECRET_KEY and URL are set."
    exit 1
fi

# Update settings
SETTINGS_FILE="/horilla/horilla/settings.py"
if [ ! -f "$SETTINGS_FILE" ]; then
    echo "Settings file not found: $SETTINGS_FILE"
    exit 1
fi

# Update Secret
sed -i "s/^SECRET_KEY = .*/SECRET_KEY = '$SECRET_KEY'/" "$SETTINGS_FILE"
echo "SECRET_KEY has been updated in the settings file."

# update CSRF
if grep -q "CSRF_TRUSTED_ORIGINS" "$SETTINGS_FILE"; then
    echo "CSRF_TRUSTED_ORIGINS already exists in the settings file."
else
    echo "CSRF_TRUSTED_ORIGINS = ['$URL']" >> "$SETTINGS_FILE"
    echo "Added CSRF_TRUSTED_ORIGINS to $SETTINGS_FILE"
fi

# Update SqlLite database
sed -i "/'NAME': BASE_DIR \/ 'TestDB_Horilla.sqlite3'/c\        'NAME': '/data/production.sqlite3'," "$SETTINGS_FILE"

# Insure data migrations
cd /horilla
python manage.py migrate

# Create sysadmin (if not created)
python manage.py createhorillauser "$FIRST_NAME" "$LAST_NAME" "$USERNAME" "$PASSWORD" "$EMAIL" "$PHONE"

# Run Horilla
echo "Running Horilla on port 8000"
python manage.py runserver 0.0.0.0:8000