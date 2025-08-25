// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React from 'react';
import {Modal, Button, Segment} from 'semantic-ui-react';

export default function ManagePromptsModal({
  open,
  onClose,
  savedPrompts,
  deletePrompt,
}) {
  return (
    <Modal open={open} onClose={onClose} size="small">
      <Modal.Header>Manage Saved Prompts</Modal.Header>
      <Modal.Content>
        {savedPrompts.length === 0 ? (
          <p>No saved prompts yet.</p>
        ) : (
          // display saved prompts in individual segments
          savedPrompts.map((prompt, idx) => (
            <Segment key={idx} style={{display: 'flex', justifyContent: 'space-between'}}>
              {/* show the saved prompt text */}
              <span style={{flex: 1, marginRight: '1em', overflowWrap: 'anywhere'}}>
                {prompt}
              </span>
              {/* delete button for prompt */}
              <Button size="mini" negative onClick={() => deletePrompt(idx)}>
                Delete
              </Button>
            </Segment>
          ))
        )}
      </Modal.Content>
      <Modal.Actions>
        <Button onClick={onClose}>Close</Button>
      </Modal.Actions>
    </Modal>
  );
}
