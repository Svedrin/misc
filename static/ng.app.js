// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

var fluxmon = angular.module('FluxmonApp', ['ui.router', 'angular-flot', 'ui.tree', 'ui.gravatar']);

fluxmon.config(function($interpolateProvider, $httpProvider, $stateProvider, $urlRouterProvider) {
    $interpolateProvider.startSymbol('{[');
    $interpolateProvider.endSymbol(']}');

    $httpProvider.defaults.xsrfHeaderName = "X-CSRFToken";
    $httpProvider.defaults.xsrfCookieName = "csrftoken";

    $urlRouterProvider.otherwise("/index");

    $stateProvider
        .state('index', {
            url: "/index",
            template: "&nbsp;"
        })
        .state('profile', {
            url: "/profile",
            templateUrl: "static/templates/profile.html",
            controller:  "ProfileCtrl"
        })
        .state('search', {
            url: "/search/:query",
            templateUrl: "static/templates/search.html",
            controller:  "SearchCtrl"
        })
        .state('tree', {
            url: "/tree",
            templateUrl: "static/templates/domain-tree.html",
            controller: "DomainTreeCtrl"
        })
        .state('domain', {
            url: "/domain/:domId",
            templateUrl: "static/templates/domain.html",
            controller:  "DomainCtrl"
        })
        .state('domain.add-host', {
            url: "/add",
            templateUrl: "static/templates/domain-addhost.html"
        })
        .state('domain.aggregatelist', {
            url: "/aggr/list",
            templateUrl: "static/templates/domain-aggregatelist.html",
            controller:  "DomainAggregateListCtrl"
        })
        .state('domain.aggregate', {
            url: "/aggr/:name",
            templateUrl: "static/templates/domain-aggregate.html",
            controller:  "DomainAggregateCtrl"
        })
        .state('node', {
            url: "/node/:nodeId",
            templateUrl: "static/templates/node.html",
            controller:  "NodeCtrl"
        })
        .state('node.checklist', {
            url: '/list',
            templateUrl: "static/templates/node-checklist.html",
            controller:  "NodeCheckListCtrl"
        })
        .state('node.check', {
            url: "/:check",
            templateUrl: "static/templates/node-check.html",
            controller:  "NodeCheckCtrl"
        })
        .state('node.check.varlist', {
            url: "/list",
            templateUrl: "static/templates/node-check-varlist.html"
        })
        .state('node.check.view', {
            url: "/view/:name",
            templateUrl: "static/templates/node-check-view.html",
            controller:  "NodeCheckViewCtrl"
        })
        .state('node.check.variable', {
            url: "/var/:name",
            templateUrl: "static/templates/node-check-var.html",
            controller:  "NodeCheckVarCtrl"
        })
        .state('token', {
            url: "/token/:token",
            templateUrl: "static/templates/token.html",
            controller:  "TokenCtrl"
        });
});

fluxmon.run(function($rootScope, $state){
  $rootScope.showIndex = function(){
    return $state.is('index');
  };
});

fluxmon.directive('ngEnter', function () {
  return function (scope, element, attrs) {
    element.bind("keydown keypress", function (event) {
      if(event.which === 13) {
        scope.$apply(function (){
          scope.$eval(attrs.ngEnter);
        });
        event.preventDefault();
      }
    });
  };
});


fluxmon.service("isMobile", function(){
    var isMobile = {
        Android: function() {
            return navigator.userAgent.match(/Android/i);
        },
        BlackBerry: function() {
            return navigator.userAgent.match(/BlackBerry/i);
        },
        iOS: function() {
            return navigator.userAgent.match(/iPhone|iPad|iPod/i);
        },
        Opera: function() {
            return navigator.userAgent.match(/Opera Mini/i);
        },
        Windows: function() {
            return navigator.userAgent.match(/IEMobile/i);
        },
        any: function() {
            return (isMobile.Android() || isMobile.BlackBerry() || isMobile.iOS() || isMobile.Opera() || isMobile.Windows());
        }
    };
    return isMobile;
});

