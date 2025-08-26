// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

// Main entry point of the summarization feature in the Indico plugin.
// This file defines the Summarize button, manages modal states,
// handles prompt selection, generates summaries, and integrates
// with Indico's API to fetch and save meeting notes.
import React, {useState, useEffect} from 'react';
import ReactDOM from 'react-dom';
import {Modal, Button, Form, Grid, GridRow, GridColumn, Header, Card, CardContent} from 'semantic-ui-react';
import {Translate} from 'indico/react/i18n';
import {getSavedPrompts, deletePrompt, getSummary, saveSummary, clearSummary} from '../utils/storage';
import {fetchSummary, fetchEventNote, saveSummaryToEvent} from '../services/summarize';
import {buildPrompt} from '../utils/prompts';
import PromptSelector from './prompt_selector';
import SummaryPreview from './summary_preview';
import ManagePromptsModal from './manage_prompts_modal';
import '../styles/ind_summarize_button.module.scss';

function SummarizeButton({eventId}) {
  // React State Definitions
  const [selectedPromptKey, setSelectedPromptKey] = useState('default'); // selected prompt type
  const [customPromptText, setCustomPromptText] = useState(''); // custom prompt content
  const [editedPromptText, setEditedPromptText] = useState(''); // manual edits to generated prompt
  const [savedPrompts, setSavedPrompts] = useState([]); // saved custom prompts
  const [summaryHtml, setSummaryHtml] = useState(''); // generated summary HTML
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false); // saving summary indicator
  const [manageModalOpen, setManageModalOpen] = useState(false); // saved prompts modal

  useEffect(() => { // load saved prompts and last generated summary from localStorage
    setSavedPrompts(getSavedPrompts());
    setSummaryHtml(getSummary());
  }, []);

  // trigger summary generation by calling the backend API
  const runSummarize = async () => {
      setLoading(true);
      setError(null);
      setSummaryHtml('');

      // build prompt: either edited, saved, or from template
      const prompt =
      editedPromptText ||
      (selectedPromptKey.startsWith('saved-')
        ? savedPrompts[parseInt(selectedPromptKey.replace('saved-', ''), 10)]
        : buildPrompt(selectedPromptKey, customPromptText));
      
      let data;
      try {
        // call backend to fetch summary
        data = await fetchSummary(eventId, prompt);
      } catch (e) {
        setError(`Error during summarization: ${handleAxiosError(e)}`);
        setLoading(false);
        return;
      }
      // if response contains the summary - display and cache it
      if (data.summary_html) {
        setSummaryHtml(data.summary_html);
        saveSummary(data.summary_html);
      } else {
        setError('No summary returned.');
      }
      setLoading(false);
    };

  // save generated summary into Indico event notes
  const handleSaveSummary = async () => {
    if (!summaryHtml) {
      setError('Summary is empty. Cannot save.');
      return;
    }
    try {
      setSaving(true);
      // fetch existing event notes
      const noteData = await fetchEventNote(eventId);
      const updatedHtml = `${noteData.html || ''}<hr><h2>Summary</h2>${summaryHtml}`;
      // save combined notes(or previous summary) + summary back to Indico
      await saveSummaryToEvent(eventId, updatedHtml, noteData.id);
    } catch (e) {
      setError(`Error during saving summary: ${handleAxiosError(e)}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Modal
        trigger={<li><a>Summarize</a></li>}
      >
        <Modal.Header>Summarize Meeting</Modal.Header>
        <Modal.Content>
          <Grid celled="internally">
            <GridRow columns={2}>
              {/* left column : prompt selection */}
              <GridColumn>
                <Header
                  as="h3"
                  content={Translate.string('Select Prompt')}
                  subheader={Translate.string('Choose a predefined prompt, edit, or create a custom one')}
                />

                {/* dropdown + manage daved prompts button (outside card) */}
                <PromptSelector.Controls
                  selectedPromptKey={selectedPromptKey}
                  setSelectedPromptKey={setSelectedPromptKey}
                  savedPrompts={savedPrompts}
                  setCustomPromptText={setCustomPromptText}
                  openManageModal={() => setManageModalOpen(true)}
                />

                {/* card with custom editor + preview of prompt + generate button */}
                <Card raised fluid style={{marginTop: '1em'}}>
                  <CardContent>
                    <Form>
                      <PromptSelector.Editor
                        selectedPromptKey={selectedPromptKey}
                        customPromptText={customPromptText}
                        setCustomPromptText={setCustomPromptText}
                        editedPromptText={editedPromptText}
                        setEditedPromptText={setEditedPromptText}
                        savedPrompts={savedPrompts}
                        setSavedPrompts={setSavedPrompts}
                      />
                      <Button
                        primary
                        type="button"
                        onClick={runSummarize}
                        disabled={loading}
                      >
                        {loading ? 'Summarizing…' : 'Generate summary'}
                      </Button>
                    </Form>
                  </CardContent>
                </Card>
              </GridColumn>

              {/* right column : summary preview */}
              <GridColumn styleName="column-divider">
                <Header as="h3" content="Preview" subheader="Summary" />
                <Card raised fluid styleName="preview-card-wrapper">
                  <CardContent>
                    <SummaryPreview
                      loading={loading}
                      error={error}
                      summaryHtml={summaryHtml}
                      saving={saving}
                      onSave={handleSaveSummary}
                      onClear={() => { setSummaryHtml(''); clearSummary(); }}
                    />
                  </CardContent>
                </Card>
              </GridColumn>
            </GridRow>
          </Grid>
        </Modal.Content>
      </Modal>

      {/* modal to manage saved prompts */}
      <ManagePromptsModal
        open={manageModalOpen}
        onClose={() => setManageModalOpen(false)}
        savedPrompts={savedPrompts}
        deletePrompt={(idx) => {
          const updated = deletePrompt(idx);
          setSavedPrompts(updated);
        }}
      />
    </>
  );
}

// custom HTML element <ind-summarize-button>
customElements.define(
  'ind-summarize-button',
  class extends HTMLElement {
    connectedCallback() {
      const eventId = this.getAttribute('event-id');
      ReactDOM.render(<SummarizeButton eventId={eventId} />, this);
    }
    disconnectedCallback() {
      ReactDOM.unmountComponentAtNode(this);
    }
  }
);
