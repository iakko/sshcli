# Implementation Plan

- [ ] 1. Extend HostBlock model with metadata fields
  - Add tags, color, and metadata_lineno fields to HostBlock class
  - Implement has_tag(), add_tag(), and remove_tag() methods
  - Update __init__ to initialize new fields with defaults
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 2. Create metadata parsing module
  - [ ] 2.1 Create sshcli/core/metadata.py file
    - Implement parse_metadata_comment() function to extract key-value from comment lines
    - Implement parse_tags() function to split comma-separated tags
    - Implement format_metadata_comments() function to generate comment lines from tags/color
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 2.2 Write unit tests for metadata parsing
    - Test parse_metadata_comment() with valid @tags and @color comments
    - Test parse_metadata_comment() with regular comments (should return None)
    - Test parse_tags() with various formats (spaces, no spaces, empty)
    - Test format_metadata_comments() output format
    - _Requirements: 1.1, 1.2, 1.5_

- [ ] 3. Enhance config parser to read metadata
  - [ ] 3.1 Modify _read_lines() to track comments
    - Create _read_lines_with_comments() that yields (lineno, text, is_comment) tuples
    - Update parse_config_files() to collect pending comments before Host blocks
    - _Requirements: 1.1, 1.3, 1.4_

  - [ ] 3.2 Implement _start_new_block_with_metadata()
    - Parse metadata from pending comments using metadata module
    - Set block.tags and block.color from parsed metadata
    - Set block.metadata_lineno to first comment line number
    - Clear pending comments after processing
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 3.3 Write integration tests for parser
    - Test parsing host with @tags comment
    - Test parsing host with @color comment
    - Test parsing host with both metadata types
    - Test parsing host without metadata (empty tags/color)
    - Test parsing multiple hosts with mixed metadata
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 4. Enhance config writer to save metadata
  - [ ] 4.1 Create format_host_block_with_metadata() function
    - Generate metadata comment lines using format_metadata_comments()
    - Append Host declaration and options
    - Return formatted string with newline
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 4.2 Create replace_host_block_with_metadata() function
    - Read existing config file lines
    - Create backup using existing _backup_file()
    - Calculate start_idx from block.metadata_lineno
    - Find end_idx of block (next Host/Match or EOF)
    - Replace lines with new formatted block including metadata
    - Write updated content back to file
    - _Requirements: 3.1, 3.2, 3.4, 3.5_

  - [ ] 4.3 Update append_host_block() to support metadata
    - Add optional tags and color parameters
    - Use format_host_block_with_metadata() instead of format_host_block()
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 4.4 Write tests for config writer
    - Test format_host_block_with_metadata() output format
    - Test replace_host_block_with_metadata() preserves other blocks
    - Test replace_host_block_with_metadata() updates metadata correctly
    - Test append_host_block() with tags
    - _Requirements: 3.1, 3.2, 3.4, 3.5_

- [ ] 5. Create CLI tag command group
  - [ ] 5.1 Create sshcli/commands/tag.py file
    - Implement tag add command to add tags to a host
    - Implement tag remove command to remove tags from a host
    - Implement tag list command to show all tags with counts
    - Implement tag show command to filter hosts by tag
    - Implement tag color command to set host color
    - Handle host pattern matching and error cases
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 5.2 Register tag command in commands/__init__.py
    - Import tag module
    - Add tag.app to main CLI app with name "tag"
    - _Requirements: 7.1_

  - [ ]* 5.3 Write CLI tests for tag commands
    - Test tag add with single and multiple tags
    - Test tag remove
    - Test tag list output format
    - Test tag show filtering
    - Test tag color setting
    - Test error handling for non-existent hosts
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 6. Enhance existing CLI commands with tag support
  - [ ] 6.1 Update list command to support --tag filter
    - Add --tag option (can be repeated)
    - Filter blocks by tags before displaying
    - Include tags in output display
    - _Requirements: 7.2, 5.1, 5.2, 5.3_

  - [ ] 6.2 Update show command to display tags
    - Add tags row to output table if block has tags
    - Add color row to output table if block has color
    - _Requirements: 7.4, 4.1, 4.2, 4.3_

  - [ ] 6.3 Update find command to support --tag filter
    - Add --tag option for filtering
    - Apply tag filter before search query
    - _Requirements: 7.2, 5.4_

  - [ ]* 6.4 Write tests for enhanced commands
    - Test list --tag filtering
    - Test show displays tags
    - Test find --tag filtering
    - _Requirements: 7.2, 7.4, 5.4_

- [ ] 7. Add tag display to UI host list
  - [ ] 7.1 Modify _populate_host_list() to show tags
    - Create tag badge widgets for each tag
    - Add colored dot indicator if block has color
    - Position tags inline after host name
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 7.2 Add tag styling
    - Define tag badge style (background, padding, border-radius)
    - Map color names to QColor values
    - Apply color to dot indicator
    - _Requirements: 4.2, 4.4_

  - [ ]* 7.3 Test tag display in UI
    - Verify tags appear for hosts with metadata
    - Verify no tags shown for hosts without metadata
    - Verify color dots display correctly
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 8. Implement UI tag filter
  - [ ] 8.1 Add tag filter dropdown to host panel
    - Create QComboBox for tag selection
    - Populate with all unique tags from loaded blocks
    - Show tag counts in dropdown items
    - Position below or next to existing filter controls
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 8.2 Implement tag filtering logic
    - Connect dropdown selection to filter handler
    - Filter _visible_blocks by selected tag
    - Combine with existing text filter
    - Update host list display
    - _Requirements: 5.2, 5.3, 5.4_

  - [ ]* 8.3 Test tag filtering
    - Verify filtering by single tag
    - Verify combination with text filter
    - Verify "All" option shows all hosts
    - _Requirements: 5.2, 5.3, 5.4_

- [ ] 9. Create UI tag edit dialog
  - [ ] 9.1 Create tag edit dialog class
    - Create new file ui/tag_dialog.py
    - Design dialog layout with current tags display
    - Add tag input field with autocomplete
    - Add color picker dropdown
    - Add Add/Remove buttons for tags
    - Add Save/Cancel buttons
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ] 9.2 Implement tag autocomplete
    - Collect all existing tags from loaded blocks
    - Create QCompleter with tag list
    - Attach to tag input field
    - _Requirements: 6.5_

  - [ ] 9.3 Wire dialog to host list context menu
    - Add "Edit Tags..." option to host right-click menu
    - Open dialog with current block's tags
    - Save changes using replace_host_block_with_metadata()
    - Reload hosts to reflect changes
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 9.4 Test tag edit dialog
    - Test adding tags
    - Test removing tags
    - Test autocomplete suggestions
    - Test color selection
    - Test save persists to config file
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 10. Update UI to use new writer function
  - [ ] 10.1 Replace calls to replace_host_block()
    - Update _add_option() to use replace_host_block_with_metadata()
    - Update _edit_option() to use replace_host_block_with_metadata()
    - Update _remove_option() to use replace_host_block_with_metadata()
    - Update _duplicate_host() to use append_host_block() with tags
    - _Requirements: 3.4, 3.5, 8.1, 8.2, 8.3_

  - [ ] 10.2 Ensure metadata is preserved on edits
    - Pass block.tags and block.color to writer functions
    - Verify tags persist after option edits
    - _Requirements: 3.4, 3.5, 8.1, 8.2_

- [ ] 11. Handle backward compatibility
  - [ ] 11.1 Test with existing configs without metadata
    - Load config files without @tags comments
    - Verify blocks parse with empty tags
    - Verify no errors or warnings
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ] 11.2 Test manual metadata editing
    - Manually add @tags comment to config file
    - Reload in CLI and UI
    - Verify tags display correctly
    - Manually edit tags in config file
    - Verify changes reflected in CLI and UI
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 11.3 Write backward compatibility tests
    - Test loading old configs without metadata
    - Test that saving without tags doesn't add empty comments
    - Test mixed configs (some hosts with tags, some without)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 12. Documentation and polish
  - [ ] 12.1 Update README with tag feature
    - Add section explaining tag metadata format
    - Add examples of @tags and @color comments
    - Document CLI tag commands
    - Document UI tag features
    - _Requirements: All_

  - [ ] 12.2 Update CHANGELOG
    - Add entry for tag feature
    - List new CLI commands
    - Note backward compatibility
    - _Requirements: All_

  - [ ]* 12.3 Add inline code documentation
    - Document metadata.py functions
    - Document new HostBlock methods
    - Document tag-related CLI commands
    - _Requirements: All_
