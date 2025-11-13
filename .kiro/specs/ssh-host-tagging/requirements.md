# Requirements Document

## Introduction

This document specifies requirements for adding a tagging and categorization system to sshcli that allows users to organize SSH hosts using metadata stored as comments in SSH config files. The system must support both CLI and UI workflows while maintaining the SSH config file as the single source of truth.

## Glossary

- **SSH_Config_Parser**: The component responsible for reading and parsing SSH configuration files
- **HostBlock**: A data structure representing a single Host entry from an SSH config file
- **Metadata_Comment**: A specially formatted comment line (prefixed with @) that stores host metadata
- **Tag**: A label assigned to a host for categorization (e.g., "prod", "web", "database")
- **Tag_Filter**: A UI or CLI mechanism to display only hosts matching specific tags
- **Config_Writer**: The component responsible for writing HostBlock data back to SSH config files

## Requirements

### Requirement 1: Parse Metadata from Comments

**User Story:** As a user, I want to add tags to my SSH hosts using comments in the config file, so that I can organize hosts without modifying SSH-compatible syntax

#### Acceptance Criteria

1. WHEN THE SSH_Config_Parser encounters a comment line starting with "# @tags:", THE SSH_Config_Parser SHALL extract the comma-separated tag values and associate them with the following HostBlock
2. WHEN THE SSH_Config_Parser encounters a comment line starting with "# @color:", THE SSH_Config_Parser SHALL extract the color value and associate it with the following HostBlock
3. WHEN multiple metadata comment lines precede a Host declaration, THE SSH_Config_Parser SHALL parse all metadata and associate it with that HostBlock
4. WHEN a HostBlock has no preceding metadata comments, THE SSH_Config_Parser SHALL create the HostBlock with empty metadata fields
5. WHEN THE SSH_Config_Parser encounters regular comments (not prefixed with @), THE SSH_Config_Parser SHALL preserve them but not parse them as metadata

### Requirement 2: Store Metadata in HostBlock Model

**User Story:** As a developer, I want the HostBlock model to store tag and color metadata, so that the application can access and manipulate this information

#### Acceptance Criteria

1. THE HostBlock data structure SHALL include a tags field containing a list of string values
2. THE HostBlock data structure SHALL include a color field containing an optional string value
3. THE HostBlock data structure SHALL include a metadata_comments field containing the original comment lines
4. WHEN a HostBlock is created without metadata, THE HostBlock SHALL initialize tags as an empty list and color as None
5. THE HostBlock data structure SHALL provide access to tags and color through public properties

### Requirement 3: Write Metadata Comments to Config Files

**User Story:** As a user, I want my tag changes to be saved back to the SSH config file as comments, so that tags persist and remain editable in any text editor

#### Acceptance Criteria

1. WHEN THE Config_Writer saves a HostBlock with tags, THE Config_Writer SHALL write a "# @tags:" comment line immediately before the Host declaration
2. WHEN THE Config_Writer saves a HostBlock with a color, THE Config_Writer SHALL write a "# @color:" comment line immediately before the Host declaration
3. WHEN THE Config_Writer saves a HostBlock without tags or color, THE Config_Writer SHALL not write metadata comment lines
4. WHEN THE Config_Writer updates an existing HostBlock, THE Config_Writer SHALL replace old metadata comments with new ones
5. THE Config_Writer SHALL preserve all non-metadata comments and SSH options when writing HostBlock data

### Requirement 4: Display Tags in UI

**User Story:** As a UI user, I want to see tags displayed next to each host in the list, so that I can quickly identify host categories

#### Acceptance Criteria

1. WHEN a HostBlock has tags, THE UI SHALL display tag badges or chips next to the host name in the list
2. WHEN a HostBlock has a color, THE UI SHALL apply visual styling (colored dot or background) to the host list item
3. WHEN a HostBlock has no tags, THE UI SHALL display the host name without tag indicators
4. THE UI SHALL display tags in a visually distinct manner from the host name
5. WHEN the user hovers over a tag, THE UI SHALL display the full tag text if truncated

### Requirement 5: Filter Hosts by Tags

**User Story:** As a user, I want to filter the host list by tags, so that I can quickly find hosts in specific categories

#### Acceptance Criteria

1. THE UI SHALL provide a tag filter control that displays all available tags
2. WHEN the user selects a tag from the filter, THE UI SHALL display only HostBlocks containing that tag
3. WHEN the user clears the tag filter, THE UI SHALL display all HostBlocks
4. THE Tag_Filter SHALL work in combination with the existing text search filter
5. THE UI SHALL display the count of hosts for each tag in the filter control

### Requirement 6: Edit Tags Through UI

**User Story:** As a UI user, I want to add, edit, or remove tags from a host, so that I can organize my hosts without manually editing config files

#### Acceptance Criteria

1. WHEN the user right-clicks a host, THE UI SHALL display a context menu option "Edit Tags"
2. WHEN the user selects "Edit Tags", THE UI SHALL open a dialog displaying current tags with options to add or remove tags
3. WHEN the user adds a new tag in the dialog, THE UI SHALL update the HostBlock and save changes to the config file
4. WHEN the user removes a tag in the dialog, THE UI SHALL update the HostBlock and save changes to the config file
5. THE tag edit dialog SHALL provide autocomplete suggestions based on existing tags from all hosts

### Requirement 7: CLI Tag Support

**User Story:** As a CLI user, I want to filter and display hosts by tags using command-line arguments, so that I can use tags in scripts and terminal workflows

#### Acceptance Criteria

1. THE CLI SHALL accept a "--tag" option that filters displayed hosts by the specified tag
2. WHEN the user runs "sshcli list --tag prod", THE CLI SHALL display only HostBlocks with the "prod" tag
3. THE CLI SHALL display tags alongside host information in list and show commands
4. WHEN the user runs "sshcli show <host>", THE CLI SHALL include tag information in the output
5. THE CLI SHALL support multiple "--tag" options to filter by multiple tags

### Requirement 8: Preserve Manual Edits

**User Story:** As a user who manually edits SSH config files, I want my tag comments to be preserved and respected, so that I can manage tags using any editor

#### Acceptance Criteria

1. WHEN a user manually adds a "# @tags:" comment in a text editor, THE SSH_Config_Parser SHALL parse and display those tags on next load
2. WHEN a user manually edits tag values in a comment, THE SSH_Config_Parser SHALL reflect those changes on next load
3. WHEN a user manually removes a "# @tags:" comment, THE SSH_Config_Parser SHALL remove tags from the HostBlock on next load
4. THE application SHALL not cache tag data between file reads
5. THE application SHALL always read tags fresh from the config file when loading hosts

### Requirement 9: Backward Compatibility

**User Story:** As a user with existing SSH configs, I want the tagging feature to work without breaking my current setup, so that I can adopt tags gradually

#### Acceptance Criteria

1. WHEN THE SSH_Config_Parser encounters a config file without metadata comments, THE SSH_Config_Parser SHALL parse all HostBlocks successfully with empty metadata
2. THE application SHALL not modify existing config files until the user explicitly adds or edits tags
3. WHEN a HostBlock without tags is saved, THE Config_Writer SHALL not add empty metadata comments
4. THE application SHALL maintain compatibility with standard SSH config syntax
5. THE application SHALL not interfere with SSH client functionality when metadata comments are present
