// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React, {useState, useEffect} from 'react';
import {Button, ButtonGroup, Icon, Popup} from 'semantic-ui-react';
import {Translate} from 'indico/react/i18n';

import '../styles/ind_summarize_button.module.scss';

export default function ActionButtons({loading, error, summaryHtml, saving, onSave, onRetry}) {

    const [isCopied, setIsCopied] = useState(false);
    const [showSavedIcon, setShowSavedIcon] = useState(false);
    const [prevSaving, setPrevSaving] = useState(false);

    useEffect(() => {
        if (isCopied) {
            const timer = setTimeout(() => setIsCopied(false), 2000);
            return () => clearTimeout(timer);
        }
    }, [isCopied]);

    useEffect(() => {
        if (prevSaving && !saving) {
            setShowSavedIcon(true);
            const timer = setTimeout(() => setShowSavedIcon(false), 2000);
            return () => clearTimeout(timer);
        }
        setPrevSaving(saving);
    }, [saving, prevSaving]);

    if (!loading) {
        return (
            <div styleName="action-buttons-container">
              <ButtonGroup basic>
                {summaryHtml && !error && (
                  <Popup trigger={
                    <Button
                      icon
                      onClick={() => {
                          navigator.clipboard.writeText(summaryHtml);
                          setIsCopied(true);
                      }}
                  >
                      <Icon
                          name={isCopied ? "check" : "copy"}
                          color={isCopied ? "green" : undefined}
                      />
                    </Button>
                  }
                    content={isCopied ? Translate.string('Copied!') : Translate.string('Copy summary')}
                    position="top center"
                  />
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
                <Popup trigger={
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
              )}
            </div>
          );
      }

    return null;
}
