$(document).ready(function() {

  // Variables
  var $nav = $('.navbar'),
      $mnav = $('.mobile-nav')
      $body = $('body'),
      $window = $(window),
      navOffsetTop = $nav.offset().top,
      mnavOffsetBot = $mnav.offset().bottom;
      $document = $(document),
      entityMap = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': '&quot;',
        "'": '&#39;',
        "/": '&#x2F;'
      }

  function init() {
    $window.on('scroll', onScroll)
    $window.on('resize', resize)
    $('a[href^="#"]').on('click', smoothScroll)
  }

  function smoothScroll(e) {
    e.preventDefault();
    $(document).off("scroll");
    var target = this.hash,
        menu = target;
    $target = $(target);
    $('html, body').stop().animate({
        'scrollTop': $target.offset().top-40
    }, 0, 'swing', function () {
        window.location.hash = target;
        $(document).on("scroll", onScroll);
    });
  }

  $("#button").click(function() {
    $('html, body').animate({
        scrollTop: $("#elementtoScrollToID").offset().top
    }, 2000);
  });
  
  function resize() {
    $body.removeClass('has-docked-nav')
    navOffsetTop = $nav.offset().top
    onScroll()
  }

  function onScroll() {
    if(navOffsetTop < $window.scrollTop() && !$body.hasClass('has-docked-nav')) {
      $body.addClass('has-docked-nav')
    }
    if(navOffsetTop > $window.scrollTop() && $body.hasClass('has-docked-nav')) {
      $body.removeClass('has-docked-nav')
    }
  }


  init();
  
});

function toggleMobileNav() {
  var m = document.getElementById("mobile-nav");
  m.style.display = (m.style.display === "block") ? "none" : "block";
}

// window.onload = function start() {
//   rotate_header_colors();
// }
// function rotate_header_colors() {
//   var i = 0;
//   var headers = document.getElementsByClassName('esg-header');
//   window.setInterval(function () {
//     var colors = ['#A6D6DF', '#EDB88D', '#D28D87', '#B7A8D1', '#A0C291', '#B29C96', '#8FADCC', 
//                   '#D57EBF', '#81E5D9', '#ECA5C8', '#BD9DDA', '#D6C849', '#F2A175'];
//     var h;
//     for (h = 0; h < headers.length; h++) {
//       headers[h].style.color = colors[i];
//     }
//     i = (i + 1) % colors.length;
//   }, 1500);
// }
