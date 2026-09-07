import StoryPublishActions from "../StoryPublishActions.jsx";

export function StepPublish({ story, token, onStoryChange }) {
  return <StoryPublishActions story={story} token={token} onStoryChange={onStoryChange} />;
}

export default StepPublish;
