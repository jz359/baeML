import React from 'react';

const FB = window.FB
class LoginComponent extends React.Component {
	
	constructor(props) {
		super(props);
		this.state = {
			loggedIn: false,
			name: ""
		}

		this.getLoginState = this.getLoginState.bind(this);
		this.statusChangeCallback = this.statusChangeCallback.bind(this);
		this.login = this.login.bind(this);
	}

	//loads the FB JS SDK
	componentDidMount() {
		window.fbAsyncInit = function() {
	       FB.init({
	        appId            : '1992517710981460',
	        autoLogAppEvents : true,
	        xfbml            : true,
	        version          : 'v2.9'
	      });
	      FB.AppEvents.logPageView();
	    };

		(function(d, s, id) {
		  var js, fjs = d.getElementsByTagName(s)[0];
		  if (d.getElementById(id)) return;
		  js = d.createElement(s); js.id = id;
		  js.src = "//connect.facebook.net/en_US/sdk.js#xfbml=1&version=v2.9&appId=1992517710981460";
		  fjs.parentNode.insertBefore(js, fjs);
		}(document, 'script', 'facebook-jssdk'));

		//attaches these methods to window so they can be called by FB SDK
		window['getLoginState'] = this.getLoginState;
		window['statusChangeCallback'] = this.statusChangeCallback;
	}

	//calls the API to retrieve info about user, changes loggedIn
	//and message
	login() {
		window.FB.api('/me', (response) => {
			this.setState({
				loggedIn: true, 
				name: response.name
			});
		});
	}

	//query status of user, either prompts to login or proceeds
	statusChangeCallback(response){
		if (response.status === 'connected') {
			console.log("bring to login page");
			this.login(); 
		} else if (response.status === 'not_authorized') {
			console.log("login thru fb");
		} else {
			console.log("handle not being logged into fb");
		}
	}

	//calls FB API's getLoginStatus
	getLoginState() { 
		window.FB.getLoginStatus(function(response) {
			this.statusChangeCallback(response);
		});
	}

	//shows either "not logged in", or person's username and the button
	render () {
		var greeting;
		if (this.state.loggedIn)
			greeting = "Hello there, " + this.state.name;
		else
			greeting = "You are not logged in";

		return (<div><p>{greeting}</p><div className="fb-login-button" 
			data-max-rows="1" 
			data-size="large" 
			data-button-type="login_with" 
			data-show-faces="false" 
			data-auto-logout-link="false" 
			data-use-continue-as="false"
			data-onlogin="getLoginState();">
			</div></div>)
	}
}

export default LoginComponent;