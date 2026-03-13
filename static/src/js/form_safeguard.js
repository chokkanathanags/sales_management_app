/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(FormController.prototype, {
    /**
     * Override beforeLeave to ensure a global alert is shown
     * if there are unsaved changes.
     */
    setup() {
        super.setup(...arguments);
        this.changedByUser = false;
        // Watch for any real user interaction (typing, clicking, changing)
        const trackInteraction = () => {
            if (this.model.root.isInEdition) {
                this.changedByUser = true;
            }
        };
        // Using native event listeners on the document to capture all interactions within the form
        const events = ['mousedown', 'keydown', 'change', 'paste'];
        events.forEach(event => {
            window.addEventListener(event, trackInteraction, { capture: true });
        });
    },

    async beforeLeave() {
        const root = this.model.root;
        // Only alert if:
        // 1. the record is dirty
        // 2. there was an actual user interaction recorded since load
        if (root.isDirty && this.changedByUser) {
            return new Promise((resolve) => {
                this.env.services.dialog.add(ConfirmationDialog, {
                    body: _t("You have unsaved changes. Do you want to continue without saving?"),
                    confirm: () => {
                        root.discard(); // Revert changes
                        this.changedByUser = false; 
                        resolve(true);   // Proceed with leaving
                    },
                    cancel: () => {
                        resolve(false);  // Stay on page
                    },
                    confirmLabel: _t("Discard and Continue"),
                    cancelLabel: _t("Stay on Page"),
                });
            });
        }
        return super.beforeLeave(...arguments);
    }
});
