"use strict";(self.webpackChunkansible_nas=self.webpackChunkansible_nas||[]).push([[2484],{3905:(e,t,n)=>{n.d(t,{Zo:()=>c,kt:()=>d});var a=n(7294);function o(e,t,n){return t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function r(e,t){var n=Object.keys(e);if(Object.getOwnPropertySymbols){var a=Object.getOwnPropertySymbols(e);t&&(a=a.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),n.push.apply(n,a)}return n}function i(e){for(var t=1;t<arguments.length;t++){var n=null!=arguments[t]?arguments[t]:{};t%2?r(Object(n),!0).forEach((function(t){o(e,t,n[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(n)):r(Object(n)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(n,t))}))}return e}function l(e,t){if(null==e)return{};var n,a,o=function(e,t){if(null==e)return{};var n,a,o={},r=Object.keys(e);for(a=0;a<r.length;a++)n=r[a],t.indexOf(n)>=0||(o[n]=e[n]);return o}(e,t);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);for(a=0;a<r.length;a++)n=r[a],t.indexOf(n)>=0||Object.prototype.propertyIsEnumerable.call(e,n)&&(o[n]=e[n])}return o}var s=a.createContext({}),p=function(e){var t=a.useContext(s),n=t;return e&&(n="function"==typeof e?e(t):i(i({},t),e)),n},c=function(e){var t=p(e.components);return a.createElement(s.Provider,{value:t},e.children)},u={inlineCode:"code",wrapper:function(e){var t=e.children;return a.createElement(a.Fragment,{},t)}},m=a.forwardRef((function(e,t){var n=e.components,o=e.mdxType,r=e.originalType,s=e.parentName,c=l(e,["components","mdxType","originalType","parentName"]),m=p(n),d=o,f=m["".concat(s,".").concat(d)]||m[d]||u[d]||r;return n?a.createElement(f,i(i({ref:t},c),{},{components:n})):a.createElement(f,i({ref:t},c))}));function d(e,t){var n=arguments,o=t&&t.mdxType;if("string"==typeof e||o){var r=n.length,i=new Array(r);i[0]=m;var l={};for(var s in t)hasOwnProperty.call(t,s)&&(l[s]=t[s]);l.originalType=e,l.mdxType="string"==typeof e?e:o,i[1]=l;for(var p=2;p<r;p++)i[p]=n[p];return a.createElement.apply(null,i)}return a.createElement.apply(null,n)}m.displayName="MDXCreateElement"},2583:(e,t,n)=>{n.r(t),n.d(t,{assets:()=>s,contentTitle:()=>i,default:()=>u,frontMatter:()=>r,metadata:()=>l,toc:()=>p});var a=n(7462),o=(n(7294),n(3905));const r={},i="Postfix Gmail relay",l={unversionedId:"applications/download-tools/postfix_gmail_relay",id:"applications/download-tools/postfix_gmail_relay",title:"Postfix Gmail relay",description:"Homepage: Postfix",source:"@site/docs/applications/download-tools/postfix_gmail_relay.md",sourceDirName:"applications/download-tools",slug:"/applications/download-tools/postfix_gmail_relay",permalink:"/docs/applications/download-tools/postfix_gmail_relay",draft:!1,editUrl:"https://github.com/davestephens/ansible-nas/tree/master/website/docs/applications/download-tools/postfix_gmail_relay.md",tags:[],version:"current",frontMatter:{},sidebar:"tutorialSidebar",previous:{title:"Overseerr",permalink:"/docs/applications/download-tools/overseerr"},next:{title:"Prowlarr",permalink:"/docs/applications/download-tools/prowlarr"}},s={},p=[{value:"Usage",id:"usage",level:2}],c={toc:p};function u(e){let{components:t,...n}=e;return(0,o.kt)("wrapper",(0,a.Z)({},c,n,{components:t,mdxType:"MDXLayout"}),(0,o.kt)("h1",{id:"postfix-gmail-relay"},"Postfix Gmail relay"),(0,o.kt)("p",null,"Homepage: ",(0,o.kt)("a",{parentName:"p",href:"https://www.postfix.org/"},"Postfix")),(0,o.kt)("p",null,"Make your NAS able to send emails using your email, by setting up Postfix with Gmail. Particularly useful if you also want to set up alerts for zpool scrubs, SMART error monitoring, or backup issues. The emails sent from your NAS will use the address specified ",(0,o.kt)("inlineCode",{parentName:"p"},"postfix_gmail_relay_email"),", which by default is equal to ",(0,o.kt)("inlineCode",{parentName:"p"},"ansible_nas_email"),". Make sure ",(0,o.kt)("inlineCode",{parentName:"p"},"postfix_gmail_relay_email")," is a Gmail account, which you need to have access to."),(0,o.kt)("h2",{id:"usage"},"Usage"),(0,o.kt)("p",null,"Update your inventory in ",(0,o.kt)("inlineCode",{parentName:"p"},"inventories/<your_inventory>/group_vars/nas.yml")," with the following:"),(0,o.kt)("ul",null,(0,o.kt)("li",{parentName:"ul"},(0,o.kt)("inlineCode",{parentName:"li"},"postfix_gmail_relay_enabled: true")),(0,o.kt)("li",{parentName:"ul"},(0,o.kt)("inlineCode",{parentName:"li"},"postfix_gmail_relay_email")," if different from ",(0,o.kt)("inlineCode",{parentName:"li"},"ansible_nas_email")),(0,o.kt)("li",{parentName:"ul"},(0,o.kt)("inlineCode",{parentName:"li"},"postfix_gmail_relay_app_password"),": create an app password in your Google account, by opening the Security tab followed by App passwords. In ",(0,o.kt)("inlineCode",{parentName:"li"},"Select app")," choose ",(0,o.kt)("inlineCode",{parentName:"li"},"Other (Custom name)")," and set any name you want, like ",(0,o.kt)("inlineCode",{parentName:"li"},"Postfix Ansible NAS"),". Set the variable to the password shown")),(0,o.kt)("p",null,"Run the ansible playbook task for postfix (",(0,o.kt)("inlineCode",{parentName:"p"},"ansible-playbook -i inventories/<your_inventory>/inventory nas.yml -b -K -t postfix"),"), then try to send yourself an email using ",(0,o.kt)("inlineCode",{parentName:"p"},'echo "Test mail from Ansible NAS" | mail -s "Test Postfix" your_email')))}u.isMDXComponent=!0}}]);