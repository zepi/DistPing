$(document).ready(function () {
    $('.navbar-burger').each(function () {
        $(this).click(function () {
            var target = $('#' + $(this).data('target'));
            
            $(this).toggleClass('is-active');
            target.toggleClass('is-active');
        });
    });

    //setInterval('refreshData();', 10000);
});

function refreshData()
{
    $('section').load('/status section > div');
}
