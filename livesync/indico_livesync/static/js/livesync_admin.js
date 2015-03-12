(function(global) {
    var $t = $T.domain('livesync');
    global.liveSyncPluginPage = function liveSyncPluginPage() {
        $('.js-delete-agent').on('click', function(e) {
            e.preventDefault();
            var $this = $(this);
            var msg = $t.gettext('Do you really want to delete this agent and all its queue entries?');
            new ConfirmPopup($t.gettext('Delete this agent?'), msg, function(confirmed) {
                if (!confirmed) {
                    return;
                }

                $('<form>', {
                    action: $this.data('href'),
                    method: 'post'
                }).appendTo('body').submit();
            }).open();
        });
    };
})(window);
