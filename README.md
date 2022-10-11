# MagicDraw importer for Confluence

This tool ingests a report output generated in MagicDraw and imports it into Confluence
via its RESTful APIs.

It requires a stereotype (`<<Publish>>`), that defines a tag (`CFL Page ID`) where the
Confluence's page ID can be stored. The ID is supposed to be defined for top-level SmartPackages,
and it creates a relationship between containment tree and Confluence's tree.

## Installation

Python package setup using virtualenv:

```
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install .
```

If using poetry:

```
$ poetry install
```

### MagicDraw setup

Import the report template. This operation is required only once:

1. Select Tools->Report wizard
2. Click on `Import` and select the file `resources/md2cfl-report.mdzip`
3. The newly imported report will appear in the list as `md2cfl`

Include the provided resource into the current project. The resource contains
the required stereotype (`<<Publish>>`) that offers a tag named `CFL Page ID`.

This procedure is required once for every project. It loads the profile containing
the stereotype `<<Publish>>`:

1. Load the project (either local or from TWC)
2. `File -> Use project -> Use local project`
3. Select `From file system`
4. Click on the button with the three dots and select the file `resources/md2cfl.mdzip`
5. Press `Next`, ensure that a shared package named `md2cfl` appears in the packages list
6. Press `Finish`

### Confluence setup

This step is required in order to set up a relationship between containment tree and confluence
pages. The importer supports two levels:

* Root pages: smart packages where a correspondent confluence page identifier is set
* Sub-pages: smart packages contained within root pages (no confluence identifier is required)

The procedure is required for each root page required. There's no limit to the number of root pages
that can be set up. A sample of this structure is contained in the `resources/md2cfl.mdzip` project.

1. Create a page, the name is not important (it'll be set by the importer)
2. Click on the three dots and select `Page information`
3. Copy the pageId parameter appearing on the URL (pageId=XXXXX), only the number is required

Then, on the project in MagicDraw:

1. Create a smart package (its location is not important) and apply the `<<Publish>>` stereotype to it
2. Open the specifications window and find `CFL Page ID` in `Tags`
3. Create a value and paste the ID of the page

The smart package can be now populated with diagrams or more smart packages containing diagrams.

## Usage

### Running the report generation in MagicDraw

1. Right-mouse click on the top level Model in the containment tree
2. Select `Generate Report -> md2cfl`
3. Find a suitable location for the output file. Its path and name is not relevant
4. Press `Save` and `No` to `Would you like to view the report after generating?`

### Running the confluence importer

*Note: the confluence user passed to the CLI arguments must be able to create and modify pages*

Using virtualenv:

```
$ source importer/.venv/bin/activate
$ md2cfl --user <confluence username> --password <confluence password> run /path/to/report.xml
```

Using poetry:

```
$ poetry run md2cfl --user <confluence username> --password <confluence password> run /path/to/report.xml
```

### Commands

```
usage: md2cfl [-h] {run,login,logout,validate} ...

optional arguments:
  -h, --help            show this help message and exit

commands:
  {run,login,logout,validate}
    run                 Run the import to confluence
    login               Add a credential set to the keyring
    logout              Remove savd login information
    validate            Validate report against schema
```

Note: further documentation regarding each command can be queried
by adding *--help* after the command, eg:

```
$ md2cfl run --help
```

#### Run

Perform the actual import. A report XML file must be passed as
argument.

Optional arguments:

* --user: confluence user to authenticate the requests against.
Overrides the user defined with the *login* command
* --password: confluence password. Overrides the one defined with the
*login* command
* --url: confluence base url for the requests
* --skip-restrictions: when specified, the importer won't apply
confluence restrictions to any imported page
* --force-updates: import everything, including content that is already
up-to-date in confluence
* --verbose: log each step in detail
* --quiet: don't print anything to the console

#### Login / Logout

*login* can be used in order to safely save the credential set
in use and avoid the need for passing user and password for every run.

It stores the password in any available keychain, if available, or
as cleartext if not.

Example:

```
$ md2cfl login cflbot
[2020-06-15 11:20:14,800] {md2cfl.__main__:149} INFO: Enter the password for user cflbot
Password:
Repeat password:
[2020-06-15 11:20:16,712] {md2cfl.__main__:165} INFO: Password stored in the keyring
[2020-06-15 11:20:16,713] {md2cfl.__main__:169} INFO: Credentials stored
```

Such login data can be then purged by using *logout*. The username
is still required as parameter:

```
$ md2cfl logout cflbot
[2020-06-15 11:21:16,176] {md2cfl.__main__:178} INFO: Removed stored user from the preferences
[2020-06-15 11:21:16,239] {md2cfl.__main__:188} INFO: Removed stored password from the keyring
```

#### Validate

XML reports generated by MD are validated against a schema before
the import takes place. The validation can be run also independently
of the import itself:

```
$ md2cfl validate samples/output.xml
[2020-06-15 11:58:20,244] {md2cfl.__main__:200} INFO: Validation successful. Version info: <VersionInfo schema version=3 stepping=1>
```

Additional information such expected schema and stepping are also shown.
