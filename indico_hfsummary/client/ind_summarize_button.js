import React,{useState} from 'react';
import {
  Modal
} from 'semantic-ui-react';
import ReactDOM from 'react-dom';



function SummarizeButton() {
    const [open, setOpen] = useState(false);
    return (
        <Modal
            open={open}
            onClose={() => setOpen(false)}
            onOpen={() => setOpen(true)}
            trigger={<li><a href="#">Summarize</a></li>}
        >
            <Modal.Header>Summarize Meeting</Modal.Header>
            <Modal.Content>
                <p>foo bar</p>
            </Modal.Content>
        </Modal>
    )
}

customElements.define(
  'ind-summarize-button',
  class extends HTMLElement {
    connectedCallback() {
        ReactDOM.render(
            <SummarizeButton />,
            this
        );
    }

    disconnectedCallback() {
        ReactDOM.unmountComponentAtNode(this);
    }
  }
);
