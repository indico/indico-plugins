// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React, {useState, useEffect} from 'react';
import {Button, ButtonGroup, Icon, Popup, Dropdown, DropdownMenu, DropdownItem} from 'semantic-ui-react';
import {Translate} from 'indico/react/i18n';

import './ActionButtons.module.scss';

function CopyToClipboardButton({summaryHtml, summaryMarkdown}) {
  const [isCopied, setIsCopied] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    if (isCopied) {
      const timer = setTimeout(() => setIsCopied(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [isCopied]);

  function handleCopy(text) {
    navigator.clipboard.writeText(text);
    setIsCopied(true);
  }

  const button = (
    <Popup
      trigger={
        <Button icon styleName="copy-button">
          <Icon name={isCopied ? 'check' : 'copy'} color={isCopied ? 'green' : undefined} />
          <Icon name="dropdown" />
        </Button>
      }
      content={isCopied ? Translate.string('Copied!') : Translate.string('Copy summary')}
      position="top center"
      disabled={isDropdownOpen}
    />
  );

  return (
    <Dropdown
      trigger={button}
      onOpen={() => setIsDropdownOpen(true)}
      onClose={() => setIsDropdownOpen(false)}
    >
      <DropdownMenu>
        <DropdownItem
          onClick={() => {
            handleCopy(summaryHtml);
          }}
          icon="code"
          text={Translate.string('Copy HTML')}
        />
        <DropdownItem
          onClick={() => {
            handleCopy(summaryMarkdown);
          }}
          icon="file alternate outline"
          text={Translate.string('Copy Markdown')}
        />
      </DropdownMenu>
    </Dropdown>
  )
}

function SaveSummaryButton({onSave, saving}) {
  const [showSavedIcon, setShowSavedIcon] = useState(false);
  const [prevSaving, setPrevSaving] = useState(false);

  useEffect(() => {
      if (prevSaving && !saving) {
          setShowSavedIcon(true);
          const timer = setTimeout(() => setShowSavedIcon(false), 2000);
          return () => clearTimeout(timer);
      }
      setPrevSaving(saving);
  }, [saving, prevSaving]);

  return (
    <Popup
      trigger={
        <Button primary={!showSavedIcon} basic={showSavedIcon} icon onClick={onSave} disabled={saving} styleName="save-button">
          {saving ? (
            <Icon name="spinner" loading />
          ) : showSavedIcon ? (
            <Icon name="check" color="green" />
          ) : (
            <Icon name="save" />
          )}
        </Button>
      }
      content={
        saving
          ? Translate.string('Saving summary...')
          : showSavedIcon
            ? Translate.string('Saved!')
            : Translate.string('Save the generated summary to the meeting minutes')
      }
      position="top center"
    />
  );
}

export default function ActionButtons({loading, error, summaryHtml, summaryMarkdown, saving, onSave, onRetry}) {
    if (!loading) {
        return (
            <div styleName="action-buttons-container">
              <ButtonGroup basic>
                {summaryHtml && !error && (
                  <CopyToClipboardButton summaryHtml={summaryHtml} summaryMarkdown={summaryMarkdown} />
                )}
                <Popup trigger={
                  <Button icon onClick={onRetry}>
                    <Icon name="undo" />
                  </Button>
                }
                  content={Translate.string('Retry generating summary')}
                  position="top center"
                />
              </ButtonGroup>

              {summaryHtml && !error && (
                <SaveSummaryButton onSave={onSave} saving={saving} />
              )}
            </div>
          );
      }

    return null;
}
