$(document).ready(function () {
    $('.navbar-burger').each(function () {
        $(this).click(function () {
            var target = $('#' + $(this).data('target'));
            
            $(this).toggleClass('is-active');
            target.toggleClass('is-active');
        });
    });
});