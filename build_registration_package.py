"""
build_registration_package.py
==============================
Generates  SVRS_FIELD_RegistrationPage.zip  — an Appian export package that
mirrors the exact format produced by Appian 25.3 Designer export.

ZIP layout (identical to reference file):
  content/_a-0000ef91-f61d-8000-bad2-01ef9001ef90_1109900.xml
  META-INF/MANIFEST.MF
  patches.xml
  META-INF/export.log

Run:
    python build_registration_package.py
"""

import zipfile
import datetime
from pathlib import Path
from xml.sax.saxutils import escape   # XML-escapes &  <  > inside <definition>

# ── Identity  (keep same env-prefix as reference; only change the numeric ID) ──
INTERFACE_NAME   = "SVRS_FIELD_RegistrationPage"
CONTENT_UUID     = "_a-0000ef91-f61d-8000-bad2-01ef9001ef90_1109900"
VERSION_UUID     = "_a-0000ef91-f61d-8000-bad2-01ef9001ef90_1109901"
APPLICATION_UUID = "d8813f1a-014e-4b4b-996a-eebbc436153e"   # same app as reference
PARENT_UUID      = "f8e423d3-55a8-4011-8e63-008a4ef11a38"   # same folder as reference
APPIAN_VERSION   = "25.3.640.0"
CREATED_ON       = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

OUTPUT_ZIP = Path(__file__).parent / f"{INTERFACE_NAME}.zip"

# ── SAIL definition (raw — will be XML-escaped before embedding) ────────────────
SAIL = """\
a!localVariables(
  local!firstName: "",
  local!lastName: "",
  local!email: "",
  local!password: "",
  local!confirmPassword: "",
  local!phone: "",
  local!dateOfBirth: "",
  local!addressLine1: "",
  local!city: "",
  local!zipCode: "",
  #"SYSTEM_SYSRULES_formLayout_v2"(
    label: "User Registration",
    contents: {
      #"SYSTEM_SYSRULES_textField"(
        label: "First Name",
        labelPosition: "ABOVE",
        placeholder: "Enter your first name",
        value: local!firstName,
        saveInto: local!firstName,
        required: true,
        helpTooltip: "Enter your legal first name."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "Last Name",
        labelPosition: "ABOVE",
        placeholder: "Enter your last name",
        value: local!lastName,
        saveInto: local!lastName,
        required: true,
        helpTooltip: "Enter your legal last name."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "Email Address",
        labelPosition: "ABOVE",
        placeholder: "example@email.com",
        value: local!email,
        saveInto: local!email,
        required: true,
        helpTooltip: "Enter a valid email address."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "Password",
        labelPosition: "ABOVE",
        placeholder: "Enter your password",
        value: local!password,
        saveInto: local!password,
        masked: true,
        required: true,
        helpTooltip: "Password must be at least 8 characters."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "Confirm Password",
        labelPosition: "ABOVE",
        placeholder: "Re-enter your password",
        value: local!confirmPassword,
        saveInto: local!confirmPassword,
        masked: true,
        required: true,
        validations: if(
          and(fn!len(local!confirmPassword) > 0, local!confirmPassword <> local!password),
          "Passwords do not match.",
          ""
        ),
        helpTooltip: "Must match the password entered above."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "Phone Number",
        labelPosition: "ABOVE",
        placeholder: "+1 (555) 000-0000",
        value: local!phone,
        saveInto: local!phone,
        required: true,
        helpTooltip: "Enter your contact phone number."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "Date of Birth",
        labelPosition: "ABOVE",
        placeholder: "MM/DD/YYYY",
        value: local!dateOfBirth,
        saveInto: local!dateOfBirth,
        required: true,
        helpTooltip: "Enter your date of birth (MM/DD/YYYY)."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "Address Line 1",
        labelPosition: "ABOVE",
        placeholder: "Street address",
        value: local!addressLine1,
        saveInto: local!addressLine1,
        required: true,
        helpTooltip: "Enter your street address."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "City",
        labelPosition: "ABOVE",
        placeholder: "Enter your city",
        value: local!city,
        saveInto: local!city,
        required: true,
        helpTooltip: "Enter your city of residence."
      ),
      #"SYSTEM_SYSRULES_textField"(
        label: "ZIP / Postal Code",
        labelPosition: "ABOVE",
        placeholder: "00000",
        value: local!zipCode,
        saveInto: local!zipCode,
        required: true,
        helpTooltip: "Enter your ZIP or postal code."
      )
    },
    buttons: #"SYSTEM_SYSRULES_buttonLayout"(
      primaryButtons: {
        #"SYSTEM_SYSRULES_buttonWidget"(
          label: "Register",
          style: "PRIMARY",
          submit: true
        )
      },
      secondaryButtons: {
        #"SYSTEM_SYSRULES_buttonWidget"(
          label: "Cancel",
          style: "SECONDARY",
          submit: false
        )
      }
    )
  )
)"""

# ── File contents ───────────────────────────────────────────────────────────────

CONTENT_XML = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<contentHaul xmlns:a="http://www.appian.com/ae/types/2009">
    <versionUuid>{VERSION_UUID}</versionUuid>
    <interface>
        <name>{INTERFACE_NAME}</name>
        <uuid>{CONTENT_UUID}</uuid>
        <description>Registration page with 10 text fields</description>
        <parentUuid>{PARENT_UUID}</parentUuid>
        <visibility>
            <advertise>false</advertise>
            <hierarchy>true</hierarchy>
            <indexable>true</indexable>
            <quota>false</quota>
            <searchable>true</searchable>
            <system>false</system>
            <unlogged>false</unlogged>
        </visibility>
        <definition>{escape(SAIL)}</definition>
        <preferredEditor>interface</preferredEditor>
        <offlineEnabled>false</offlineEnabled>
        <isCustom>false</isCustom>
    </interface>
    <roleMap public="true">
        <role inherit="true" allowForAll="false" name="readers">
            <users/>
            <groups/>
        </role>
        <role inherit="true" allowForAll="false" name="authors">
            <users/>
            <groups/>
        </role>
        <role inherit="true" allowForAll="false" name="administrators">
            <users/>
            <groups/>
        </role>
        <role inherit="false" allowForAll="false" name="denyReaders">
            <users/>
            <groups/>
        </role>
        <role inherit="false" allowForAll="false" name="denyAuthors">
            <users/>
            <groups/>
        </role>
        <role inherit="false" allowForAll="false" name="denyAdministrators">
            <users/>
            <groups/>
        </role>
    </roleMap>
    <history>
        <historyInfo versionUuid="{VERSION_UUID}"/>
    </history>
</contentHaul>
"""

MANIFEST_MF = f"""\
Manifest-Version: 1.0
Appian-Version: {APPIAN_VERSION}
Created-On: {CREATED_ON}

"""

PATCHES_XML = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<applicationPatches>
    <applicationPatch>
        <applicationUuid>{APPLICATION_UUID}</applicationUuid>
        <packageInfo>
            <url></url>
        </packageInfo>
        <patchContents>
            <item>
                <type>content</type>
                <uuids>
                    <uuid>{CONTENT_UUID}</uuid>
                </uuids>
            </item>
        </patchContents>
    </applicationPatch>
</applicationPatches>
"""

EXPORT_LOG = f"""\
Success (1):
content {CONTENT_UUID} "{INTERFACE_NAME}"

Referenced precedents that were not exported (0):

Trace:
{CREATED_ON} DEBUG content {CONTENT_UUID} Begin transport.
{CREATED_ON} DEBUG content {CONTENT_UUID} Retrieving object data.
{CREATED_ON} DEBUG content {CONTENT_UUID} Setting uuids of object references.
{CREATED_ON} DEBUG content {CONTENT_UUID} Exporting binary resources.
{CREATED_ON} DEBUG content {CONTENT_UUID} Serializing object to XML.
{CREATED_ON} DEBUG content {CONTENT_UUID} Object transported.
"""


# ── Build ZIP ───────────────────────────────────────────────────────────────────

def build():
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"content/{CONTENT_UUID}.xml", CONTENT_XML.encode("utf-8"))
        zf.writestr("META-INF/MANIFEST.MF",        MANIFEST_MF.encode("utf-8"))
        zf.writestr("patches.xml",                  PATCHES_XML.encode("utf-8"))
        zf.writestr("META-INF/export.log",          EXPORT_LOG.encode("utf-8"))

    size_kb = OUTPUT_ZIP.stat().st_size / 1024
    print(f"[✓] Created: {OUTPUT_ZIP.name}  ({size_kb:.1f} KB)")
    print("    Contents:")
    with zipfile.ZipFile(OUTPUT_ZIP) as zf:
        for info in zf.infolist():
            print(f"      {info.filename}  ({info.file_size} bytes)")


if __name__ == "__main__":
    build()
