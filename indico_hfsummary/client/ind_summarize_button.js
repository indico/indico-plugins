import {useState} from 'react';
import {
  Modal
} from 'semantic-ui-react';
import ReactDOM from 'react-dom';

const [open, setOpen] = useState(false);

function SummarizeButton() {
    return (
        <Modal
            open={open}
            onClose={() => setOpen(false)}
            onOpen={() => setOpen(true)}
            trigger={<li><div className="manage-notes-container"><a href="#">Summarize</a></div></li>}
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
